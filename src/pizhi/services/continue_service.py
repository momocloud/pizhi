from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from pizhi.core.config import load_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.core.templates import render_checkpoint_summary
from pizhi.services.maintenance import format_checkpoint_maintenance
from pizhi.services.outline_service import OutlineService
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.write_service import WriteService


@dataclass(frozen=True, slots=True)
class ContinueResult:
    chapter_range: tuple[int, int]
    checkpoint_paths: list[Path]


class ContinueService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.paths = project_paths(project_root)
        self.config = load_config(self.paths.config_file)
        self.index_store = ChapterIndexStore(self.paths.chapter_index_file)
        self.outline_service = OutlineService(project_root)
        self.write_service = WriteService(project_root)

    def continue_project(
        self,
        count: int,
        outline_response_file: Path | None = None,
        chapter_responses_dir: Path | None = None,
        direction: str = "",
    ) -> ContinueResult:
        chapter_range = self.determine_chapter_range(count)
        start, end = chapter_range
        self.outline_service.expand(
            chapter_range=chapter_range,
            response_file=outline_response_file,
            direction=direction,
        )

        written_numbers: list[int] = []
        maintenance_by_chapter: dict[int, MaintenanceResult | None] = {}
        if chapter_responses_dir is not None:
            for chapter_number in range(start, end + 1):
                response_path = chapter_responses_dir / f"ch{chapter_number:03d}_response.md"
                if not response_path.exists():
                    raise FileNotFoundError(response_path)
                write_result = self.write_service.write(chapter_number=chapter_number, response_file=response_path)
                written_numbers.append(chapter_number)
                maintenance_by_chapter[chapter_number] = write_result.maintenance_result

        checkpoint_paths: list[Path] = []
        interval = self.config.consistency.checkpoint_interval
        for offset in range(interval, len(written_numbers) + 1, interval):
            chunk = written_numbers[offset - interval : offset]
            checkpoint_paths.append(self._write_checkpoint(chunk, maintenance_by_chapter))

        return ContinueResult(
            chapter_range=chapter_range,
            checkpoint_paths=checkpoint_paths,
        )

    def determine_chapter_range(self, count: int) -> tuple[int, int]:
        records = self.index_store.read_all()
        drafted_statuses = {"drafted", "reviewed", "compiled"}
        drafted_numbers = [int(record["n"]) for record in records if record.get("status") in drafted_statuses]
        start = (max(drafted_numbers) + 1) if drafted_numbers else 1
        end = start + count - 1
        return start, end

    def _determine_chapter_range(self, count: int) -> tuple[int, int]:
        return self.determine_chapter_range(count)

    def _write_checkpoint(
        self,
        chapter_numbers: list[int],
        maintenance_by_chapter: dict[int, MaintenanceResult | None],
    ) -> Path:
        entries: list[dict[str, object]] = []
        for chapter_number in chapter_numbers:
            chapter_dir = self.paths.chapter_dir(chapter_number)
            meta = json.loads((chapter_dir / "meta.json").read_text(encoding="utf-8"))
            text = (chapter_dir / "text.md").read_text(encoding="utf-8")
            characters = (chapter_dir / "characters.md").read_text(encoding="utf-8")
            relationships = (chapter_dir / "relationships.md").read_text(encoding="utf-8")
            entries.append(
                {
                    "number": chapter_number,
                    "title": meta["chapter_title"],
                    "summary": " ".join(text.split())[:100],
                    "character_state": _first_content_line(characters),
                    "relationship_state": _first_content_line(relationships),
                    "introduced_ids": [item["id"] for item in meta["foreshadowing"]["introduced"]],
                    "resolved_ids": [item["id"] for item in meta["foreshadowing"]["resolved"]],
                }
            )
        maintenance_text = format_checkpoint_maintenance(
            [(chapter_number, maintenance_by_chapter.get(chapter_number)) for chapter_number in chapter_numbers]
        )

        checkpoint_path = self.paths.cache_dir / (
            f"checkpoint-ch{chapter_numbers[0]:03d}-ch{chapter_numbers[-1]:03d}.md"
        )
        checkpoint_path.write_text(
            render_checkpoint_summary(entries, maintenance_text=maintenance_text),
            encoding="utf-8",
            newline="\n",
        )
        return checkpoint_path


def _first_content_line(raw: str) -> str:
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("|"):
            return stripped
    return ""
