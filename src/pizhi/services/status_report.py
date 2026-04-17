from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.domain.foreshadowing import ForeshadowingEntry
from pizhi.domain.project_state import ChapterState
from pizhi.services.project_snapshot import load_project_snapshot

STATUS_ORDER = ("planned", "outlined", "drafted", "reviewed", "compiled")
PENDING_QUEUE_ORDER = ("outlined", "drafted", "reviewed")
NEAR_PAYOFF_LEAD = 5


@dataclass(slots=True)
class StatusReport:
    project_name: str
    total_planned: int
    per_volume: int
    chapter_counts: dict[str, int]
    latest_chapter: int | None
    next_chapter: int
    compiled_volumes: int
    recent_chapters: list[ChapterState]
    pending_chapters: dict[str, list[ChapterState]]
    active_foreshadowing: list[ForeshadowingEntry]
    active_foreshadowing_count: int
    near_payoff_foreshadowing: list[ForeshadowingEntry]
    overdue_foreshadowing: list[ForeshadowingEntry]


def build_status_report(project_root: Path) -> StatusReport:
    snapshot = load_project_snapshot(project_root)
    chapter_counts = {status: 0 for status in STATUS_ORDER}
    pending_chapters = {status: [] for status in PENDING_QUEUE_ORDER}

    for chapter in snapshot.chapters.values():
        chapter_counts.setdefault(chapter.status, 0)
        chapter_counts[chapter.status] += 1
        if chapter.status in pending_chapters:
            pending_chapters[chapter.status].append(chapter)

    for status in pending_chapters:
        pending_chapters[status].sort(key=lambda chapter: chapter.number)

    active_foreshadowing = [
        entry for entry in snapshot.foreshadowing_entries if entry.section == "Active"
    ]
    overdue_foreshadowing = [
        entry for entry in active_foreshadowing if _is_overdue(entry, snapshot.next_chapter)
    ]
    near_payoff_foreshadowing = [
        entry
        for entry in active_foreshadowing
        if not _is_overdue(entry, snapshot.next_chapter)
        and _is_near_payoff(entry, snapshot.next_chapter)
    ]

    paths = project_paths(project_root)
    compiled_volumes = len(list(paths.manuscript_dir.glob("vol_*.md"))) if paths.manuscript_dir.exists() else 0

    return StatusReport(
        project_name=snapshot.project_name,
        total_planned=snapshot.total_planned,
        per_volume=snapshot.per_volume,
        chapter_counts=chapter_counts,
        latest_chapter=snapshot.latest_chapter,
        next_chapter=snapshot.next_chapter,
        compiled_volumes=compiled_volumes,
        recent_chapters=snapshot.recent_chapters,
        pending_chapters=pending_chapters,
        active_foreshadowing=active_foreshadowing,
        active_foreshadowing_count=len(active_foreshadowing),
        near_payoff_foreshadowing=near_payoff_foreshadowing,
        overdue_foreshadowing=overdue_foreshadowing,
    )


def _is_near_payoff(entry: ForeshadowingEntry, next_chapter: int) -> bool:
    if entry.planned_payoff is None:
        return False

    start_chapter = entry.planned_payoff.start_chapter
    near_window_start = start_chapter - NEAR_PAYOFF_LEAD

    if entry.planned_payoff.open_ended:
        return near_window_start <= next_chapter <= start_chapter

    end_chapter = entry.planned_payoff.end_chapter or start_chapter
    return near_window_start <= next_chapter <= end_chapter


def _is_overdue(entry: ForeshadowingEntry, next_chapter: int) -> bool:
    if entry.planned_payoff is None:
        return False
    if entry.planned_payoff.open_ended:
        return False
    deadline = entry.planned_payoff.end_chapter or entry.planned_payoff.start_chapter
    return deadline < next_chapter
