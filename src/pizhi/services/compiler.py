from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths


COMPILABLE_STATUSES = {"drafted", "reviewed", "compiled"}


@dataclass(frozen=True, slots=True)
class CompileTarget:
    volume: int | None = None
    chapter: int | None = None
    chapter_start: int | None = None
    chapter_end: int | None = None

    def __post_init__(self) -> None:
        modes = sum(
            value is not None
            for value in (self.volume, self.chapter, self.chapter_start, self.chapter_end)
        )
        if modes == 0:
            raise ValueError("compile target must specify exactly one target mode")
        if self.volume is not None and any(
            value is not None for value in (self.chapter, self.chapter_start, self.chapter_end)
        ):
            raise ValueError("compile target must specify exactly one target mode")
        if self.chapter is not None and any(
            value is not None for value in (self.volume, self.chapter_start, self.chapter_end)
        ):
            raise ValueError("compile target must specify exactly one target mode")
        if self.chapter_start is not None or self.chapter_end is not None:
            if self.chapter_start is None or self.chapter_end is None:
                raise ValueError("compile target range must specify both chapter_start and chapter_end")
            if self.chapter_start > self.chapter_end:
                raise ValueError("chapter range start must be <= end")
            if self.volume is not None or self.chapter is not None:
                raise ValueError("compile target must specify exactly one target mode")


def compile_manuscript(project_root: Path, *, target: CompileTarget | None = None) -> list[Path]:
    paths = project_paths(project_root)
    store = ChapterIndexStore(paths.chapter_index_file)
    records = store.read_all()

    if target is None:
        written_files = _compile_by_volume(paths, records)
    elif target.volume is not None:
        written_files = _compile_targeted_volume(paths, records, target.volume)
    elif target.chapter is not None:
        written_files = _compile_targeted_chapter(paths, records, target.chapter)
    else:
        written_files = _compile_targeted_range(paths, records, target.chapter_start, target.chapter_end)

    for record in records:
        if record.get("status") == "compiled":
            store.upsert(record)

    return written_files


def _compile_by_volume(paths, records: list[dict]) -> list[Path]:
    grouped: dict[int, list[dict]] = {}
    for record in records:
        if record.get("status") in COMPILABLE_STATUSES:
            grouped.setdefault(int(record["vol"]), []).append(record)

    written_files: list[Path] = []
    for volume, items in sorted(grouped.items()):
        written_files.extend(_write_manuscript(paths, items, destination=paths.manuscript_dir / f"vol_{volume:02d}.md", title=f"Volume {volume:02d}"))
    return written_files


def _compile_targeted_volume(paths, records: list[dict], volume: int) -> list[Path]:
    selected = [record for record in records if int(record["vol"]) == volume and record.get("status") in COMPILABLE_STATUSES]
    if not selected:
        raise ValueError(f"no compilable chapters found for volume {volume:02d}")
    return _write_manuscript(
        paths,
        selected,
        destination=paths.manuscript_dir / f"vol_{volume:02d}.md",
        title=f"Volume {volume:02d}",
    )


def _compile_targeted_chapter(paths, records: list[dict], chapter: int) -> list[Path]:
    selected = [record for record in records if int(record["n"]) == chapter and record.get("status") in COMPILABLE_STATUSES]
    if not selected:
        raise ValueError(f"no compilable chapter found for chapter {chapter:03d}")
    return _write_manuscript(
        paths,
        selected,
        destination=paths.manuscript_dir / f"ch{chapter:03d}.md",
        title=f"Chapter {chapter:03d}",
    )


def _compile_targeted_range(paths, records: list[dict], start: int, end: int) -> list[Path]:
    selected = [
        record
        for record in records
        if start <= int(record["n"]) <= end and record.get("status") in COMPILABLE_STATUSES
    ]
    if not selected:
        raise ValueError(f"no compilable chapters found for chapter range {start:03d}-{end:03d}")
    return _write_manuscript(
        paths,
        selected,
        destination=paths.manuscript_dir / f"ch{start:03d}-ch{end:03d}.md",
        title=f"Chapters {start:03d}-{end:03d}",
    )


def _write_manuscript(paths, records: list[dict], *, destination: Path, title: str) -> list[Path]:
    ordered = sorted(records, key=lambda item: int(item["n"]))
    parts = [f"# {title}", ""]
    for record in ordered:
        chapter_number = int(record["n"])
        text_path = paths.chapter_dir(chapter_number).joinpath("text.md")
        chapter_text = text_path.read_text(encoding="utf-8").strip()
        parts.append(f"## {record['title']}")
        parts.append("")
        parts.append(chapter_text)
        parts.append("")
        record["status"] = "compiled"

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8", newline="\n")
    return [destination]
