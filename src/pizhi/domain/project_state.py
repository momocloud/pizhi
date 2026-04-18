from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pizhi.domain.foreshadowing import ForeshadowingEntry
from pizhi.domain.timeline import TimelineEntry


@dataclass(slots=True)
class ChapterArtifacts:
    text_exists: bool
    characters_exists: bool
    relationships_exists: bool
    meta_exists: bool


@dataclass(slots=True)
class ChapterState:
    number: int
    title: str
    volume: int
    status: str
    summary: str
    updated: str
    chapter_dir: Path
    artifacts: ChapterArtifacts
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ArchiveRange:
    start_chapter: int
    end_chapter: int


@dataclass(slots=True)
class ProjectSnapshot:
    project_name: str
    total_planned: int
    per_volume: int
    chapters: dict[int, ChapterState]
    latest_chapter: int | None
    next_chapter: int
    recent_chapters: list[ChapterState]
    timeline_entries: list[TimelineEntry]
    active_or_referenced_foreshadowing: list[ForeshadowingEntry]
    major_turning_points: list[TimelineEntry]
    eligible_archive_ranges: list[ArchiveRange]
    existing_timeline_archive_ranges: list[ArchiveRange]
    existing_foreshadowing_archive_ranges: list[ArchiveRange]
    foreshadowing_entries: list[ForeshadowingEntry]
