from __future__ import annotations

from pathlib import Path

from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths


COMPILABLE_STATUSES = {"drafted", "reviewed", "compiled"}


def compile_manuscript(project_root: Path) -> list[Path]:
    paths = project_paths(project_root)
    store = ChapterIndexStore(paths.chapter_index_file)
    records = store.read_all()

    grouped: dict[int, list[dict]] = {}
    for record in records:
        if record.get("status") in COMPILABLE_STATUSES:
            grouped.setdefault(int(record["vol"]), []).append(record)

    written_files: list[Path] = []
    for volume, items in sorted(grouped.items()):
        ordered = sorted(items, key=lambda item: int(item["n"]))
        parts = [f"# Volume {volume:02d}", ""]
        for record in ordered:
            chapter_number = int(record["n"])
            chapter_text = paths.chapter_dir(chapter_number).joinpath("text.md").read_text(encoding="utf-8").strip()
            parts.append(f"## {record['title']}")
            parts.append("")
            parts.append(chapter_text)
            parts.append("")
            record["status"] = "compiled"

        destination = paths.manuscript_dir / f"vol_{volume:02d}.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8", newline="\n")
        written_files.append(destination)

    for record in records:
        if record.get("status") == "compiled":
            store.upsert(record)

    return written_files
