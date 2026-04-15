from __future__ import annotations

import re
from typing import Any


SECTION_NAMES = ("Active", "Referenced", "Resolved", "Abandoned")
SECTION_RE = re.compile(
    r"^## (?P<name>Active|Referenced|Resolved|Abandoned)\s*$\n(?P<content>.*?)(?=^## (?:Active|Referenced|Resolved|Abandoned)\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)
ENTRY_RE = re.compile(r"^### (?P<id>F\d+).*?(?=^### F\d+|\Z)", re.MULTILINE | re.DOTALL)


def update_foreshadowing_tracker(current_text: str, operations: dict[str, Any]) -> str:
    header, sections = _parse_sections(current_text)

    for item in operations.get("introduced", []):
        entry = _format_introduced_entry(item)
        sections["Active"] = _upsert_entry(sections["Active"], item["id"], entry)

    for item in operations.get("resolved", []):
        resolved_id = item["id"]
        sections["Active"] = _remove_entry(sections["Active"], resolved_id)
        sections["Referenced"] = _remove_entry(sections["Referenced"], resolved_id)
        sections["Resolved"] = _upsert_entry(sections["Resolved"], resolved_id, _format_resolved_entry(item))

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


def _format_resolved_entry(item: dict[str, Any]) -> str:
    return (
        f"### {item['id']}\n"
        f"- **Resolution**: {item.get('resolution', '')}\n"
    )


def _upsert_entry(section_text: str, entry_id: str, new_block: str) -> str:
    cleaned = _remove_entry(section_text, entry_id).strip()
    parts = [cleaned] if cleaned else []
    parts.append(new_block.strip())
    return "\n\n".join(parts).strip()


def _remove_entry(section_text: str, entry_id: str) -> str:
    blocks = [match.group(0).strip() for match in ENTRY_RE.finditer(section_text)]
    kept = [block for block in blocks if not block.startswith(f"### {entry_id}")]
    return "\n\n".join(kept).strip()


def _entry_ids(section_text: str) -> set[str]:
    return {match.group("id") for match in ENTRY_RE.finditer(section_text)}
