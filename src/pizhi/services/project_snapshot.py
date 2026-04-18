from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pizhi.core.config import default_config
from pizhi.core.config import load_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.domain.foreshadowing import parse_tracker_entries
from pizhi.domain.foreshadowing import ForeshadowingEntry
from pizhi.domain.project_state import ArchiveRange
from pizhi.domain.project_state import ChapterArtifacts
from pizhi.domain.project_state import ChapterState
from pizhi.domain.project_state import ProjectSnapshot
from pizhi.domain.timeline import TimelineEntry
from pizhi.domain.timeline import parse_timeline_entries


ARCHIVE_FILE_RE = re.compile(
    r"^(?P<artifact>timeline|foreshadowing)_ch(?P<start>\d{3})-(?P<end>\d{3})\.md$"
)
ARCHIVE_BLOCK_SIZE = 50


def load_project_snapshot(project_root: Path) -> ProjectSnapshot:
    paths = project_paths(project_root)
    if paths.config_file.exists():
        config = load_config(paths.config_file)
    else:
        config = default_config(name=project_root.name)

    chapters: dict[int, ChapterState] = {}
    records = ChapterIndexStore(paths.chapter_index_file).read_all()

    for record in records:
        number = int(record["n"])
        chapter_dir = paths.chapter_dir(number)
        chapters[number] = ChapterState(
            number=number,
            title=str(record.get("title", "")),
            volume=int(record.get("vol", 0)),
            status=str(record.get("status", "planned")),
            summary=str(record.get("summary", "")),
            updated=str(record.get("updated", "")),
            chapter_dir=chapter_dir,
            artifacts=ChapterArtifacts(
                text_exists=(chapter_dir / "text.md").exists(),
                characters_exists=(chapter_dir / "characters.md").exists(),
                relationships_exists=(chapter_dir / "relationships.md").exists(),
                meta_exists=(chapter_dir / "meta.json").exists(),
            ),
            metadata=_load_json(chapter_dir / "meta.json"),
        )

    recent_chapters = [chapters[number] for number in sorted(chapters, reverse=True)]
    latest_chapter = recent_chapters[0].number if recent_chapters else None
    next_chapter = 1 if latest_chapter is None else latest_chapter + 1
    timeline_entries = _load_timeline_entries(paths)
    foreshadowing_entries: list[ForeshadowingEntry] = []
    if paths.foreshadowing_file.exists():
        foreshadowing_entries = parse_tracker_entries(paths.foreshadowing_file.read_text(encoding="utf-8"))
    active_or_referenced_foreshadowing = [
        entry for entry in foreshadowing_entries if entry.section in {"Active", "Referenced"}
    ]
    major_turning_points = [entry for entry in timeline_entries if entry.is_major_turning_point]

    return ProjectSnapshot(
        project_name=config.project.name,
        total_planned=config.chapters.total_planned,
        per_volume=config.chapters.per_volume,
        chapters=chapters,
        latest_chapter=latest_chapter,
        next_chapter=next_chapter,
        recent_chapters=recent_chapters,
        timeline_entries=timeline_entries,
        active_or_referenced_foreshadowing=active_or_referenced_foreshadowing,
        major_turning_points=major_turning_points,
        eligible_archive_ranges=_sealed_ranges(latest_chapter),
        existing_timeline_archive_ranges=_discover_archive_ranges(paths.archive_dir, "timeline"),
        existing_foreshadowing_archive_ranges=_discover_archive_ranges(paths.archive_dir, "foreshadowing"),
        foreshadowing_entries=foreshadowing_entries,
    )


def _load_timeline_entries(paths) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    if paths.timeline_file.exists():
        entries.extend(parse_timeline_entries(paths.timeline_file.read_text(encoding="utf-8")))

    for archive_path in _archive_paths(paths.archive_dir, "timeline"):
        entries.extend(parse_timeline_entries(archive_path.read_text(encoding="utf-8")))

    entries.sort(key=lambda entry: (entry.chapter_number, entry.event_index))
    return entries


def _sealed_ranges(latest_chapter: int | None) -> list[ArchiveRange]:
    if latest_chapter is None or latest_chapter < ARCHIVE_BLOCK_SIZE:
        return []

    sealed_end = (latest_chapter // ARCHIVE_BLOCK_SIZE) * ARCHIVE_BLOCK_SIZE
    ranges: list[ArchiveRange] = []
    for start_chapter in range(1, sealed_end + 1, ARCHIVE_BLOCK_SIZE):
        ranges.append(ArchiveRange(start_chapter=start_chapter, end_chapter=start_chapter + ARCHIVE_BLOCK_SIZE - 1))
    return ranges


def _discover_archive_ranges(archive_dir: Path, artifact: str) -> list[ArchiveRange]:
    ranges: list[ArchiveRange] = []
    for path in _archive_paths(archive_dir, artifact):
        match = ARCHIVE_FILE_RE.fullmatch(path.name)
        if match is None:
            continue
        ranges.append(
            ArchiveRange(
                start_chapter=int(match.group("start")),
                end_chapter=int(match.group("end")),
            )
        )
    ranges.sort(key=lambda item: (item.start_chapter, item.end_chapter))
    return ranges


def _archive_paths(archive_dir: Path, artifact: str) -> list[Path]:
    if not archive_dir.exists():
        return []
    return sorted(
        path
        for path in archive_dir.glob(f"{artifact}_ch*.md")
        if ARCHIVE_FILE_RE.fullmatch(path.name)
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
