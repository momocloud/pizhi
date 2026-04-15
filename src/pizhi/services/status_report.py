from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.core.config import default_config
from pizhi.core.config import load_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths

STATUS_ORDER = ("planned", "outlined", "drafted", "reviewed", "compiled")


@dataclass(slots=True)
class StatusReport:
    project_name: str
    total_planned: int
    per_volume: int
    chapter_counts: dict[str, int]
    latest_chapter: int | None
    next_chapter: int
    compiled_volumes: int


def build_status_report(project_root: Path) -> StatusReport:
    paths = project_paths(project_root)
    if paths.config_file.exists():
        config = load_config(paths.config_file)
    else:
        config = default_config(name=project_root.name)

    records = ChapterIndexStore(paths.chapter_index_file).read_all()
    chapter_counts = {status: 0 for status in STATUS_ORDER}
    latest_chapter: int | None = None

    for record in records:
        status = str(record.get("status", "planned"))
        chapter_counts.setdefault(status, 0)
        chapter_counts[status] += 1

        number = int(record["n"])
        if latest_chapter is None or number > latest_chapter:
            latest_chapter = number

    compiled_volumes = len(list(paths.manuscript_dir.glob("vol_*.md"))) if paths.manuscript_dir.exists() else 0
    next_chapter = 1 if latest_chapter is None else latest_chapter + 1

    return StatusReport(
        project_name=config.project.name,
        total_planned=config.chapters.total_planned,
        per_volume=config.chapters.per_volume,
        chapter_counts=chapter_counts,
        latest_chapter=latest_chapter,
        next_chapter=next_chapter,
        compiled_volumes=compiled_volumes,
    )
