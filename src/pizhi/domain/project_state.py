from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


@dataclass(slots=True)
class ProjectSnapshot:
    project_name: str
    total_planned: int
    per_volume: int
    chapters: dict[int, ChapterState]
    latest_chapter: int | None
    next_chapter: int
    recent_chapters: list[ChapterState]
