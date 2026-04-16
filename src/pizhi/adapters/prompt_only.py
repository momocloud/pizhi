from __future__ import annotations

from dataclasses import asdict
from datetime import UTC
from datetime import datetime
import json
from pathlib import Path

from pizhi.adapters.base import PromptArtifact
from pizhi.adapters.base import PromptRequest
from pizhi.core.paths import project_paths


class PromptOnlyAdapter:
    def __init__(self, project_root: Path) -> None:
        self.paths = project_paths(project_root)

    def prepare(self, request: PromptRequest) -> PromptArtifact:
        packet_id = f"{request.command_name}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        self.paths.prompts_dir.mkdir(parents=True, exist_ok=True)

        prompt_path = self.paths.prompts_dir / f"{packet_id}.md"
        manifest_path = self.paths.prompts_dir / f"{packet_id}.json"

        prompt_path.write_text(request.prompt_text, encoding="utf-8", newline="\n")
        manifest_path.write_text(
            json.dumps(
                {
                    "packet_id": packet_id,
                    **asdict(request),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

        return PromptArtifact(
            packet_id=packet_id,
            prompt_path=prompt_path,
            manifest_path=manifest_path,
        )
