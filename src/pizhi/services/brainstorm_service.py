from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pizhi.adapters.base import PromptArtifact
from pizhi.adapters.base import PromptRequest
from pizhi.adapters.prompt_only import PromptOnlyAdapter
from pizhi.core.paths import project_paths


SECTION_PATTERN = re.compile(
    r"^## (?P<name>[a-z_]+)\s*$\n(?P<content>.*?)(?=^## [a-z_]+\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class BrainstormResult:
    prompt_artifact: PromptArtifact


class BrainstormService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.paths = project_paths(project_root)
        self.adapter = PromptOnlyAdapter(project_root)

    def build_prompt_request(self) -> PromptRequest:
        return PromptRequest(
            command_name="brainstorm",
            prompt_text=self._build_prompt(),
            metadata={"command": "brainstorm"},
            referenced_files=[
                ".pizhi/global/synopsis.md",
                ".pizhi/global/worldview.md",
                ".pizhi/global/rules.md",
                ".pizhi/global/outline_global.md",
                ".pizhi/global/foreshadowing.md",
                ".pizhi/chapters/ch000/characters.md",
                ".pizhi/chapters/ch000/relationships.md",
            ],
        )

    def prepare_prompt(self, request: PromptRequest) -> PromptArtifact:
        return self.adapter.prepare(request)

    def run(self, response_file: Path | None = None) -> BrainstormResult:
        artifact = self.prepare_prompt(self.build_prompt_request())

        if response_file is not None:
            self.apply_response(response_file.read_text(encoding="utf-8"))
            self.paths.last_session_file.write_text(
                "# Last Session\n\n- Command: brainstorm\n- Status: applied\n",
                encoding="utf-8",
                newline="\n",
            )
        else:
            self.paths.last_session_file.write_text(
                "# Last Session\n\n- Command: brainstorm\n- Status: prompt_prepared\n",
                encoding="utf-8",
                newline="\n",
            )

        return BrainstormResult(prompt_artifact=artifact)

    def apply_response(self, raw_response: str) -> None:
        sections = parse_brainstorm_response(raw_response)
        _write_text(self.paths.synopsis_file, sections["synopsis"])
        _write_text(self.paths.worldview_file, sections["worldview"])
        _write_text(self.paths.global_dir / "rules.md", sections["rules"])
        _write_text(self.paths.foreshadowing_file, sections["foreshadowing"])
        _write_text(self.paths.global_dir / "outline_global.md", sections["outline_global"])
        _write_text(self.paths.chapter_zero_dir / "characters.md", sections["characters"])
        _write_text(self.paths.chapter_zero_dir / "relationships.md", sections["relationships"])

    def _build_prompt(self) -> str:
        return (
            "# Brainstorm Request\n\n"
            "Generate a project bootstrap packet with sections:\n"
            "## synopsis\n"
            "## worldview\n"
            "## rules\n"
            "## foreshadowing\n"
            "## outline_global\n"
            "## characters\n"
            "## relationships\n"
        )


def parse_brainstorm_response(raw: str) -> dict[str, str]:
    sections = {
        match.group("name"): match.group("content").strip()
        for match in SECTION_PATTERN.finditer(raw)
    }

    required_names = (
        "synopsis",
        "worldview",
        "rules",
        "foreshadowing",
        "outline_global",
        "characters",
        "relationships",
    )
    missing = [name for name in required_names if name not in sections]
    if missing:
        raise ValueError(f"missing brainstorm sections: {', '.join(missing)}")
    return sections


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8", newline="\n")
