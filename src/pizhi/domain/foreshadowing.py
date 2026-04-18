from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


SECTION_NAMES = ("Active", "Referenced", "Resolved", "Abandoned")
SECTION_RE = re.compile(
    r"^## (?P<name>Active|Referenced|Resolved|Abandoned)\s*$\n(?P<content>.*?)(?=^## (?:Active|Referenced|Resolved|Abandoned)\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)
ENTRY_BLOCK_RE = re.compile(r"^### .+?(?=^### |\Z)", re.MULTILINE | re.DOTALL)
ENTRY_ID_RE = re.compile(r"^### (?P<id>F\d+)(?:\s|\Z)", re.MULTILINE)
PAYOFF_RE = re.compile(r"^ch(?P<start>\d{3})(?:(?:-ch(?P<end>\d{3}))|(?P<open>\+))?$", re.IGNORECASE)
ENTRY_HEADER_RE = re.compile(r"^### (?P<id>F\d+)(?: \| Priority: (?P<priority>.+))?$")
ENTRY_FIELD_RE = re.compile(r"^- \*\*(?P<name>[^*]+)\*\*: ?(?P<value>.*)$")
CLOSE_CHAPTER_RE = re.compile(r"^ch(?P<chapter>\d{3})$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class PlannedPayoff:
    start_chapter: int
    end_chapter: int | None
    open_ended: bool


@dataclass(frozen=True, slots=True)
class ForeshadowingEntry:
    entry_id: str
    section: str
    description: str
    planned_payoff: PlannedPayoff | None
    priority: str | None
    related_characters: list[str]
    resolution: str | None
    closed_in_chapter: int | None
    referenced: bool


def update_foreshadowing_tracker(
    current_text: str,
    operations: dict[str, Any],
    chapter_number: int | None = None,
) -> str:
    header, sections = _parse_sections(current_text)

    for item in operations.get("introduced", []):
        entry = _format_introduced_entry(item)
        sections["Active"] = _upsert_entry(sections["Active"], item["id"], entry)

    for item in operations.get("resolved", []):
        resolved_id = item["id"]
        sections["Active"] = _remove_entry(sections["Active"], resolved_id)
        sections["Referenced"] = _remove_entry(sections["Referenced"], resolved_id)
        sections["Resolved"] = _upsert_entry(
            sections["Resolved"],
            resolved_id,
            _format_resolved_entry(item, chapter_number),
        )

    for item in operations.get("referenced", []):
        referenced_id = item["id"] if isinstance(item, dict) else str(item)
        if referenced_id not in _entry_ids(sections["Active"]) and referenced_id not in _entry_ids(sections["Referenced"]):
            sections["Referenced"] = _upsert_entry(
                sections["Referenced"],
                referenced_id,
                f"### {referenced_id}\n- **Referenced**: true\n",
            )

    parts = [header.rstrip(), ""]
    for name in SECTION_NAMES:
        parts.append(f"## {name}")
        content = sections[name].strip()
        if content:
            parts.append(content)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def tracker_ids_by_section(current_text: str) -> dict[str, set[str]]:
    _, sections = _parse_sections(current_text)
    return {
        "Active": _entry_ids(sections["Active"]),
        "Referenced": _entry_ids(sections["Referenced"]),
        "Resolved": _entry_ids(sections["Resolved"]),
        "Abandoned": _entry_ids(sections["Abandoned"]),
    }


def parse_planned_payoff(value: str) -> PlannedPayoff:
    match = PAYOFF_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Unsupported planned payoff value: {value!r}")

    start_chapter = int(match.group("start"))
    end_value = match.group("end")
    open_ended = match.group("open") == "+"
    end_chapter = None if open_ended else int(end_value) if end_value else start_chapter
    return PlannedPayoff(
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        open_ended=open_ended,
    )


def parse_tracker_entries(current_text: str) -> list[ForeshadowingEntry]:
    _, sections = _parse_sections(current_text)
    entries: list[ForeshadowingEntry] = []
    for section_name in SECTION_NAMES:
        for match in ENTRY_BLOCK_RE.finditer(sections[section_name]):
            entry = _try_parse_entry_block(match.group(0), section_name)
            if entry is not None:
                entries.append(entry)
    return entries


def _parse_sections(current_text: str) -> tuple[str, dict[str, str]]:
    matches = list(SECTION_RE.finditer(current_text))
    if matches:
        header = current_text[: matches[0].start()].strip() or "# Foreshadowing Tracker"
    else:
        header = "# Foreshadowing Tracker"
    sections = {name: "" for name in SECTION_NAMES}
    for match in matches:
        sections[match.group("name")] = match.group("content").strip()
    return header, sections


def _format_introduced_entry(item: dict[str, Any]) -> str:
    related = ", ".join(item.get("related_characters", []))
    return (
        f"### {item['id']} | Priority: {item.get('priority', 'medium')}\n"
        f"- **Description**: {item.get('desc', '')}\n"
        f"- **Planned Payoff**: {item.get('planned_payoff', '')}\n"
        f"- **Related Characters**: {related}\n"
    )


def _format_resolved_entry(item: dict[str, Any], chapter_number: int | None = None) -> str:
    lines = [
        f"### {item['id']}",
        f"- **Resolution**: {item.get('resolution', '')}",
    ]
    if chapter_number is not None:
        lines.append(f"- **Resolved In**: ch{chapter_number:03d}")
    return "\n".join(lines) + "\n"


def _upsert_entry(section_text: str, entry_id: str, new_block: str) -> str:
    cleaned = _remove_entry(section_text, entry_id).strip()
    parts = [cleaned] if cleaned else []
    parts.append(new_block.strip())
    return "\n\n".join(parts).strip()


def _remove_entry(section_text: str, entry_id: str) -> str:
    blocks = [match.group(0).strip() for match in ENTRY_BLOCK_RE.finditer(section_text)]
    kept = [block for block in blocks if _entry_block_id(block) != entry_id]
    return "\n\n".join(kept).strip()


def _entry_ids(section_text: str) -> set[str]:
    return {match.group("id") for match in ENTRY_ID_RE.finditer(section_text)}


def _parse_entry_block(block: str, section_name: str) -> ForeshadowingEntry:
    lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
    header_match = ENTRY_HEADER_RE.fullmatch(lines[0])
    if header_match is None:
        raise ValueError(f"Unsupported foreshadowing header: {lines[0]!r}")

    fields: dict[str, str] = {}
    for line in lines[1:]:
        field_match = ENTRY_FIELD_RE.fullmatch(line)
        if field_match:
            fields[field_match.group("name")] = field_match.group("value")

    payoff_text = fields.get("Planned Payoff", "")
    related_text = fields.get("Related Characters", "")
    closed_in_chapter = _parse_closed_in_chapter(fields)
    return ForeshadowingEntry(
        entry_id=header_match.group("id"),
        section=section_name,
        description=fields.get("Description", ""),
        planned_payoff=parse_planned_payoff(payoff_text) if payoff_text else None,
        priority=header_match.group("priority"),
        related_characters=[name.strip() for name in related_text.split(",") if name.strip()],
        resolution=fields.get("Resolution"),
        closed_in_chapter=closed_in_chapter,
        referenced=fields.get("Referenced", "").lower() == "true",
    )


def _try_parse_entry_block(block: str, section_name: str) -> ForeshadowingEntry | None:
    try:
        return _parse_entry_block(block, section_name)
    except ValueError:
        return None


def _entry_block_id(block: str) -> str | None:
    first_line = block.strip().splitlines()[0]
    header_match = ENTRY_HEADER_RE.fullmatch(first_line)
    if header_match is None:
        return None
    return header_match.group("id")


def _parse_closed_in_chapter(fields: dict[str, str]) -> int | None:
    for field_name in ("Resolved In", "Abandoned In"):
        value = fields.get(field_name)
        if not value:
            continue
        match = CLOSE_CHAPTER_RE.fullmatch(value.strip())
        if match is None:
            continue
        return int(match.group("chapter"))
    return None
