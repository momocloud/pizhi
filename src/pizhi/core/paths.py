from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    root: Path

    @property
    def workspace_dir(self) -> Path:
        return self.root / ".pizhi"

    @property
    def global_dir(self) -> Path:
        return self.workspace_dir / "global"

    @property
    def chapters_dir(self) -> Path:
        return self.workspace_dir / "chapters"

    @property
    def manuscript_dir(self) -> Path:
        return self.root / "manuscript"

    @property
    def config_file(self) -> Path:
        return self.workspace_dir / "config.yaml"

    @property
    def chapter_index_file(self) -> Path:
        return self.chapters_dir / "index.jsonl"


def project_paths(root: Path) -> ProjectPaths:
    return ProjectPaths(root=root.resolve())
