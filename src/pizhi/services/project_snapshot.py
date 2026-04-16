from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pizhi.core.config import default_config
from pizhi.core.config import load_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.domain.project_state import ChapterArtifacts
from pizhi.domain.project_state import ChapterState
from pizhi.domain.project_state import ProjectSnapshot


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

    return ProjectSnapshot(
        project_name=config.project.name,
        total_planned=config.chapters.total_planned,
        per_volume=config.chapters.per_volume,
        chapters=chapters,
        latest_chapter=latest_chapter,
        next_chapter=next_chapter,
        recent_chapters=recent_chapters,
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
