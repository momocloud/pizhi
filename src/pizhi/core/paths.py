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

    @property
    def hooks_dir(self) -> Path:
        return self.workspace_dir / "hooks"

    @property
    def cache_dir(self) -> Path:
        return self.workspace_dir / "cache"

    @property
    def prompts_dir(self) -> Path:
        return self.cache_dir / "prompts"

    @property
    def archive_dir(self) -> Path:
        return self.workspace_dir / "archive"

    @property
    def chapter_zero_dir(self) -> Path:
        return self.chapters_dir / "ch000"

    @property
    def synopsis_file(self) -> Path:
        return self.global_dir / "synopsis.md"

    @property
    def synopsis_candidate_file(self) -> Path:
        return self.global_dir / "synopsis_candidate.md"

    @property
    def worldview_file(self) -> Path:
        return self.global_dir / "worldview.md"

    @property
    def timeline_file(self) -> Path:
        return self.global_dir / "timeline.md"

    @property
    def foreshadowing_file(self) -> Path:
        return self.global_dir / "foreshadowing.md"

    @property
    def last_session_file(self) -> Path:
        return self.cache_dir / "last_session.md"

    def chapter_dir(self, chapter_number: int) -> Path:
        return self.chapters_dir / f"ch{chapter_number:03d}"


def project_paths(root: Path) -> ProjectPaths:
    return ProjectPaths(root=root.resolve())
