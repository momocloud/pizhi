from __future__ import annotations

from pathlib import Path

from pizhi.core.config import default_config
from pizhi.core.config import save_config
from pizhi.core.paths import project_paths
from pizhi.core.templates import initial_markdown_files


class ProjectInitService:
    def __init__(self, root: Path) -> None:
        self.paths = project_paths(root)

    def initialize(
        self,
        name: str,
        genre: str,
        total_chapters: int,
        per_volume: int,
        pov: str,
    ) -> None:
        self._create_directories()
        save_config(
            self.paths.config_file,
            default_config(
                name=name,
                genre=genre,
                total_chapters=total_chapters,
                per_volume=per_volume,
                pov=pov,
            ),
        )
        self._write_markdown_files(name=name, genre=genre)
        self.paths.chapter_index_file.touch(exist_ok=True)

    def _create_directories(self) -> None:
        for path in (
            self.paths.workspace_dir,
            self.paths.global_dir,
            self.paths.chapters_dir,
            self.paths.chapter_zero_dir,
            self.paths.hooks_dir,
            self.paths.cache_dir,
            self.paths.archive_dir,
            self.paths.manuscript_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _write_markdown_files(self, name: str, genre: str) -> None:
        for relative_path, content in initial_markdown_files(name, genre).items():
            destination = self.paths.workspace_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
