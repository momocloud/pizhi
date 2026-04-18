from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pizhi.adapters.base import PromptArtifact
from pizhi.adapters.base import PromptRequest
from pizhi.adapters.prompt_only import PromptOnlyAdapter
from pizhi.core.paths import project_paths
from pizhi.services.chapter_context import ChapterContext
from pizhi.services.chapter_context import build_chapter_context
from pizhi.services.chapter_writer import ChapterWriteResult
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.maintenance import run_after_write


@dataclass(frozen=True, slots=True)
class WriteResult:
    prompt_artifact: PromptArtifact
    chapter_result: ChapterWriteResult | None
    maintenance_result: MaintenanceResult | None


class WriteService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.adapter = PromptOnlyAdapter(project_root)

    def write(self, chapter_number: int, response_file: Path | None = None) -> WriteResult:
        context = build_chapter_context(self.project_root, chapter_number)
        artifact = self.adapter.prepare(
            PromptRequest(
                command_name="write",
                prompt_text=_build_prompt(context),
                metadata={"chapter": chapter_number},
                referenced_files=[
                    ".pizhi/global/synopsis.md",
                    ".pizhi/global/worldview.md",
                    ".pizhi/global/rules.md",
                    ".pizhi/global/foreshadowing.md",
                    f".pizhi/chapters/ch{chapter_number:03d}/outline.md",
                ],
            )
        )

        chapter_result = None
        maintenance_result = None
        if response_file is not None:
            raw_response = response_file.read_text(encoding="utf-8")
            chapter_result = apply_chapter_response(
                self.project_root,
                chapter_number=chapter_number,
                raw_response=raw_response,
            )
            _restore_synopsis_candidate(self.project_root, raw_response)
            maintenance_result = run_after_write(self.project_root)

        return WriteResult(
            prompt_artifact=artifact,
            chapter_result=chapter_result,
            maintenance_result=maintenance_result,
        )


def _build_prompt(context: ChapterContext) -> str:
    sections = [f"# Chapter Write Request\n\nChapter: {context.chapter_number}"]
    for name, content in context.required_inputs.items():
        sections.append(f"## {name}\n{content}")
    for name, content in context.optional_inputs.items():
        if content:
            sections.append(f"## {name}\n{content}")
    return "\n\n".join(sections).strip() + "\n"


SYNOPSIS_NEW_BLOCK_RE = re.compile(r"^## synopsis_new\s*$\n(?P<content>.*)\Z", re.MULTILINE | re.DOTALL)


def _restore_synopsis_candidate(project_root: Path, raw_response: str) -> None:
    match = SYNOPSIS_NEW_BLOCK_RE.search(raw_response)
    if match is None:
        return

    synopsis_candidate = match.group("content").strip()
    if not synopsis_candidate:
        return

    paths = project_paths(project_root)
    paths.synopsis_candidate_file.write_text(
        synopsis_candidate + "\n",
        encoding="utf-8",
        newline="\n",
    )
