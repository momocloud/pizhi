from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.core.paths import project_paths


@dataclass(frozen=True, slots=True)
class ChapterContext:
    chapter_number: int
    required_inputs: dict[str, str]
    optional_inputs: dict[str, str]


def build_chapter_context(project_root: Path, chapter_number: int) -> ChapterContext:
    paths = project_paths(project_root)
    chapter_dir = paths.chapter_dir(chapter_number)
    previous_dir = paths.chapter_dir(chapter_number - 1) if chapter_number > 1 else None
    second_previous_dir = paths.chapter_dir(chapter_number - 2) if chapter_number > 2 else None

    required_inputs = {
        "synopsis": _read_text(paths.synopsis_file),
        "worldview": _read_text(paths.worldview_file),
        "rules": _read_text(paths.global_dir / "rules.md"),
        "foreshadowing": _read_text(paths.foreshadowing_file),
        "current_outline": _read_text(chapter_dir / "outline.md"),
        "previous_text": _read_text(previous_dir / "text.md") if previous_dir else "",
        "previous_characters": _read_text(previous_dir / "characters.md") if previous_dir else "",
        "previous_relationships": _read_text(previous_dir / "relationships.md") if previous_dir else "",
    }
    optional_inputs = {
        "second_previous_text": _read_text(second_previous_dir / "text.md") if second_previous_dir else "",
    }
    return ChapterContext(
        chapter_number=chapter_number,
        required_inputs=required_inputs,
        optional_inputs=optional_inputs,
    )


def _read_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""
