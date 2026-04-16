from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PromptRequest:
    command_name: str
    prompt_text: str
    metadata: dict[str, Any]
    referenced_files: list[str]


@dataclass(frozen=True, slots=True)
class PromptArtifact:
    packet_id: str
    prompt_path: Path
    manifest_path: Path
