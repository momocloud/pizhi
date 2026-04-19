from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

from pizhi.adapters.base import PromptArtifact
from pizhi.adapters.base import PromptRequest
from pizhi.adapters.prompt_only import PromptOnlyAdapter
from pizhi.core.config import load_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths


BLOCK_PATTERN = re.compile(
    r"^## ch(?P<number>\d{3}) \| (?P<title>.+?)\s*$\n(?P<body>.*?)(?=^## ch\d{3} \| |\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class OutlineBlock:
    chapter_number: int
    title: str
    body: str


@dataclass(frozen=True, slots=True)
class OutlineResult:
    prompt_artifact: PromptArtifact
    blocks: list[OutlineBlock]


class OutlineService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.paths = project_paths(project_root)
        self.adapter = PromptOnlyAdapter(project_root)
        self.index_store = ChapterIndexStore(self.paths.chapter_index_file)
        self.config = load_config(self.paths.config_file)

    def expand(
        self,
        chapter_range: tuple[int, int],
        response_file: Path | None = None,
        direction: str = "",
    ) -> OutlineResult:
        start, end = chapter_range
        artifact = self.prepare_prompt(self.build_prompt_request(chapter_range, direction=direction))

        blocks: list[OutlineBlock] = []
        if response_file is not None:
            blocks = self.apply_response(response_file.read_text(encoding="utf-8"))
            self.paths.last_session_file.write_text(
                f"# Last Session\n\n- Command: outline expand\n- Chapters: ch{start:03d}-ch{end:03d}\n- Status: applied\n",
                encoding="utf-8",
                newline="\n",
            )
        else:
            self.paths.last_session_file.write_text(
                f"# Last Session\n\n- Command: outline expand\n- Chapters: ch{start:03d}-ch{end:03d}\n- Status: prompt_prepared\n",
                encoding="utf-8",
                newline="\n",
            )

        return OutlineResult(prompt_artifact=artifact, blocks=blocks)

    def build_prompt_request(self, chapter_range: tuple[int, int], direction: str = "") -> PromptRequest:
        start, end = chapter_range
        return PromptRequest(
            command_name="outline-expand",
            prompt_text=self._build_prompt(start, end, direction),
            metadata={"chapters": [start, end], "direction": direction},
            referenced_files=[
                ".pizhi/global/synopsis.md",
                ".pizhi/global/outline_global.md",
                ".pizhi/global/worldview.md",
                ".pizhi/global/rules.md",
            ],
        )

    def prepare_prompt(self, request: PromptRequest) -> PromptArtifact:
        return self.adapter.prepare(request)

    def apply_response(self, raw_response: str) -> list[OutlineBlock]:
        blocks = parse_outline_response(raw_response)
        self.apply_blocks(blocks)
        return blocks

    def apply_blocks(self, blocks: list[OutlineBlock]) -> None:
        for block in blocks:
            chapter_dir = self.paths.chapter_dir(block.chapter_number)
            chapter_dir.mkdir(parents=True, exist_ok=True)
            (chapter_dir / "outline.md").write_text(
                f"# 第{block.chapter_number:03d}章 {block.title}\n\n{block.body.strip()}\n",
                encoding="utf-8",
                newline="\n",
            )
            volume = ((block.chapter_number - 1) // self.config.chapters.per_volume) + 1
            self.index_store.upsert(
                {
                    "n": block.chapter_number,
                    "title": block.title,
                    "vol": volume,
                    "status": "outlined",
                    "updated": date.today().isoformat(),
                }
            )

        outline_path = self.paths.global_dir.joinpath("outline_global.md")
        existing_text = ""
        if outline_path.exists():
            existing_text = outline_path.read_text(encoding="utf-8").rstrip()

        outline_lines: list[str] = []
        for block in blocks:
            outline_lines.append(f"## ch{block.chapter_number:03d} | {block.title}")
            outline_lines.append(block.body.strip())
            outline_lines.append("")

        new_text = "\n".join(outline_lines).rstrip()
        if existing_text:
            merged_text = f"{existing_text}\n\n{new_text}\n"
        else:
            merged_text = f"# Global Outline\n\n{new_text}\n"
        outline_path.write_text(
            merged_text,
            encoding="utf-8",
            newline="\n",
        )

    def _build_prompt(self, start: int, end: int, direction: str) -> str:
        direction_text = direction if direction else "Continue the established arc."
        return (
            "# Outline Expansion Request\n\n"
            f"Expand chapters {start}-{end}.\n\n"
            f"Direction: {direction_text}\n\n"
            "Return blocks in this format:\n"
            "## ch001 | 标题\n"
            "- beat 1\n"
            "- beat 2\n"
        )


def parse_outline_response(raw: str) -> list[OutlineBlock]:
    blocks = [
        OutlineBlock(
            chapter_number=int(match.group("number")),
            title=match.group("title").strip(),
            body=match.group("body").strip(),
        )
        for match in BLOCK_PATTERN.finditer(raw)
    ]
    if not blocks:
        raise ValueError("outline response is missing chapter blocks")
    return blocks
