from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pizhi.core.paths import project_paths
from pizhi.domain.foreshadowing import ForeshadowingEntry
from pizhi.domain.project_state import ArchiveRange
from pizhi.domain.timeline import TimelineEntry
from pizhi.services.project_snapshot import load_project_snapshot


DEFAULT_TIMELINE_TEXT = "# Timeline\n"
DEFAULT_FORESHADOWING_TEXT = "# Foreshadowing Tracker\n\n## Active\n\n## Referenced\n\n## Resolved\n\n## Abandoned\n"
TIMELINE_HEADER_RE = re.compile(r"^## (?P<id>T\d{3}-\d{2})$")
FORESHADOWING_HEADER_RE = re.compile(r"^### (?P<id>F\d+)(?: \| Priority: .+)?$")


@dataclass(frozen=True, slots=True)
class ArchiveFinding:
    description: str
    artifact: str
    archive_range: ArchiveRange | None


@dataclass(slots=True)
class ArchiveResult:
    findings: list[ArchiveFinding]


def rotate_archives(project_root: Path) -> ArchiveResult:
    snapshot = load_project_snapshot(project_root)
    paths = project_paths(project_root)
    findings: list[ArchiveFinding] = []

    _rotate_timeline_archives(paths, snapshot.timeline_entries, snapshot.eligible_archive_ranges, findings)
    _rotate_foreshadowing_archives(paths, snapshot.foreshadowing_entries, snapshot.eligible_archive_ranges, findings)
    return ArchiveResult(findings=findings)


def _rotate_timeline_archives(
    paths,
    timeline_entries: list[TimelineEntry],
    pending_ranges: list[ArchiveRange],
    findings: list[ArchiveFinding],
) -> None:
    live_text = _read_text(paths.timeline_file, DEFAULT_TIMELINE_TEXT)
    archived_timeline_entries: list[TimelineEntry] = []

    for archive_range in pending_ranges:
        ranged_entries = _timeline_entries_for_range(timeline_entries, archive_range)
        if not ranged_entries:
            continue

        expected_text = _render_timeline_archive(archive_range, ranged_entries)
        archive_path = _archive_path(paths.archive_dir, "timeline", archive_range)
        if not _sync_archive_file(archive_path, expected_text):
            findings.append(
                ArchiveFinding(
                    description=(
                        f"timeline archive conflict for ch{archive_range.start_chapter:03d}-{archive_range.end_chapter:03d}"
                    ),
                    artifact="timeline",
                    archive_range=archive_range,
                )
            )
            continue

        archived_timeline_entries.extend(ranged_entries)

    if archived_timeline_entries:
        updated_text = _remove_timeline_entries_from_text(live_text, archived_timeline_entries)
        if updated_text != live_text:
            _write_text(paths.timeline_file, updated_text)


def _rotate_foreshadowing_archives(
    paths,
    foreshadowing_entries: list[ForeshadowingEntry],
    pending_ranges: list[ArchiveRange],
    findings: list[ArchiveFinding],
) -> None:
    live_text = _read_text(paths.foreshadowing_file, DEFAULT_FORESHADOWING_TEXT)
    archived_entries: list[ForeshadowingEntry] = []

    for entry in foreshadowing_entries:
        if entry.section in {"Resolved", "Abandoned"} and entry.closed_in_chapter is None:
            findings.append(
                ArchiveFinding(
                    description=f"foreshadowing entry {entry.entry_id} is missing close chapter metadata",
                    artifact="foreshadowing",
                    archive_range=None,
                )
            )

    for archive_range in pending_ranges:
        ranged_entries = _foreshadowing_entries_for_range(foreshadowing_entries, archive_range)
        if not ranged_entries:
            continue

        expected_text = _render_foreshadowing_archive(archive_range, ranged_entries)
        archive_path = _archive_path(paths.archive_dir, "foreshadowing", archive_range)
        if not _sync_archive_file(archive_path, expected_text):
            findings.append(
                ArchiveFinding(
                    description=(
                        "foreshadowing archive conflict for "
                        f"ch{archive_range.start_chapter:03d}-{archive_range.end_chapter:03d}"
                    ),
                    artifact="foreshadowing",
                    archive_range=archive_range,
                )
            )
            continue

        archived_entries.extend(ranged_entries)

    if archived_entries:
        updated_text = _remove_foreshadowing_entries_from_text(live_text, archived_entries)
        if updated_text != live_text:
            _write_text(paths.foreshadowing_file, updated_text)


def _timeline_entries_for_range(entries: list[TimelineEntry], archive_range: ArchiveRange) -> list[TimelineEntry]:
    return [
        entry
        for entry in entries
        if _range_contains(archive_range, entry.chapter_number)
    ]


def _foreshadowing_entries_for_range(entries: list[ForeshadowingEntry], archive_range: ArchiveRange) -> list[ForeshadowingEntry]:
    archivable = [
        entry
        for entry in entries
        if _is_archivable_foreshadowing(entry) and _range_contains(archive_range, _entry_close_chapter(entry))
    ]
    return sorted(archivable, key=_foreshadowing_archive_sort_key)


def _is_archivable_foreshadowing(entry: ForeshadowingEntry) -> bool:
    return entry.section in {"Resolved", "Abandoned"} and entry.closed_in_chapter is not None


def _entry_close_chapter(entry: ForeshadowingEntry) -> int:
    if entry.closed_in_chapter is None:
        raise ValueError(f"foreshadowing entry {entry.entry_id} is missing close chapter metadata")
    return entry.closed_in_chapter


def _range_contains(archive_range: ArchiveRange, chapter_number: int) -> bool:
    return archive_range.start_chapter <= chapter_number <= archive_range.end_chapter


def _archive_path(archive_dir: Path, artifact: str, archive_range: ArchiveRange) -> Path:
    return archive_dir / f"{artifact}_ch{archive_range.start_chapter:03d}-{archive_range.end_chapter:03d}.md"


def _sync_archive_file(path: Path, expected_text: str) -> bool:
    if path.exists():
        return path.read_text(encoding="utf-8") == expected_text

    _write_text(path, expected_text)
    return True


def _render_timeline_archive(archive_range: ArchiveRange, entries: list[TimelineEntry]) -> str:
    lines = [f"# Timeline Archive: ch{archive_range.start_chapter:03d}-ch{archive_range.end_chapter:03d}", ""]
    for entry in sorted(entries, key=lambda item: (item.chapter_number, item.event_index)):
        lines.extend(
            [
                f"## {entry.event_id}",
                f"- **时间**: {entry.at}",
                f"- **事件**: {entry.event}",
                f"- **闪回**: {'是' if entry.is_flashback else '否'}",
                f"- **重大转折**: {'是' if entry.is_major_turning_point else '否'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_timeline_live(entries: list[TimelineEntry]) -> str:
    if not entries:
        return DEFAULT_TIMELINE_TEXT

    lines = ["# Timeline", ""]
    for entry in sorted(entries, key=lambda item: (item.chapter_number, item.event_index)):
        lines.extend(
            [
                f"## {entry.event_id}",
                f"- **时间**: {entry.at}",
                f"- **事件**: {entry.event}",
                f"- **闪回**: {'是' if entry.is_flashback else '否'}",
                f"- **重大转折**: {'是' if entry.is_major_turning_point else '否'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_foreshadowing_archive(archive_range: ArchiveRange, entries: list[ForeshadowingEntry]) -> str:
    return _render_foreshadowing_sections(
        f"# Foreshadowing Archive: ch{archive_range.start_chapter:03d}-ch{archive_range.end_chapter:03d}",
        sorted(entries, key=_foreshadowing_archive_sort_key),
        sections=("Resolved", "Abandoned"),
    )


def _render_foreshadowing_live(entries: list[ForeshadowingEntry]) -> str:
    return _render_foreshadowing_sections(
        "# Foreshadowing Tracker",
        entries,
        sections=("Active", "Referenced", "Resolved", "Abandoned"),
    )


def _render_foreshadowing_sections(header: str, entries: list[ForeshadowingEntry], *, sections: tuple[str, ...]) -> str:
    grouped: dict[str, list[ForeshadowingEntry]] = {section: [] for section in sections}
    for entry in entries:
        if entry.section in grouped:
            grouped[entry.section].append(entry)

    lines = [header, ""]
    for section in sections:
        lines.append(f"## {section}")
        section_entries = grouped[section]
        if section_entries:
            lines.append("")
            for entry in sorted(section_entries, key=_foreshadowing_archive_sort_key):
                lines.extend(_render_foreshadowing_entry(entry))
                lines.append("")
        else:
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _foreshadowing_archive_sort_key(entry: ForeshadowingEntry) -> tuple[int, int, str]:
    section_order = {"Resolved": 0, "Abandoned": 1}.get(entry.section, 2)
    close_chapter = entry.closed_in_chapter if entry.closed_in_chapter is not None else 10**9
    return section_order, close_chapter, entry.entry_id


def _remove_timeline_entries_from_text(text: str, entries: list[TimelineEntry]) -> str:
    target_ids = {entry.event_id for entry in entries}
    return _remove_block_text(text, target_ids=target_ids, header_re=TIMELINE_HEADER_RE, stop_prefixes=("## ",))


def _remove_foreshadowing_entries_from_text(text: str, entries: list[ForeshadowingEntry]) -> str:
    target_ids = {entry.entry_id for entry in entries}
    return _remove_block_text(text, target_ids=target_ids, header_re=FORESHADOWING_HEADER_RE, stop_prefixes=("### ", "## "))


def _remove_block_text(
    text: str,
    *,
    target_ids: set[str],
    header_re: re.Pattern[str],
    stop_prefixes: tuple[str, ...],
) -> str:
    lines = text.splitlines()
    remaining: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        header_match = header_re.fullmatch(line)
        if header_match is not None and header_match.group("id") in target_ids:
            index += 1
            while index < len(lines) and not lines[index].startswith(stop_prefixes):
                index += 1
            continue

        remaining.append(line)
        index += 1

    return "\n".join(remaining).rstrip() + ("\n" if remaining else "")


def _render_foreshadowing_entry(entry: ForeshadowingEntry) -> list[str]:
    lines = [f"### {entry.entry_id}" + (f" | Priority: {entry.priority}" if entry.priority else "")]
    if entry.section in {"Active", "Abandoned"}:
        lines.append(f"- **Description**: {entry.description}")
        if entry.planned_payoff is not None:
            if entry.planned_payoff.open_ended:
                payoff = f"ch{entry.planned_payoff.start_chapter:03d}+"
            elif entry.planned_payoff.end_chapter == entry.planned_payoff.start_chapter:
                payoff = f"ch{entry.planned_payoff.start_chapter:03d}"
            else:
                payoff = f"ch{entry.planned_payoff.start_chapter:03d}-ch{entry.planned_payoff.end_chapter:03d}"
            lines.append(f"- **Planned Payoff**: {payoff}")
        if entry.related_characters:
            lines.append(f"- **Related Characters**: {', '.join(entry.related_characters)}")
        if entry.section == "Abandoned" and entry.closed_in_chapter is not None:
            lines.append(f"- **Abandoned In**: ch{entry.closed_in_chapter:03d}")
    elif entry.section == "Referenced":
        lines.append("- **Referenced**: true")
    elif entry.section == "Resolved":
        lines.append(f"- **Resolution**: {entry.resolution or ''}")
        if entry.closed_in_chapter is not None:
            lines.append(f"- **Resolved In**: ch{entry.closed_in_chapter:03d}")
    return lines


def _read_text(path: Path, default: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return default


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
