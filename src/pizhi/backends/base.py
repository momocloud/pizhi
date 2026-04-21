from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pizhi.adapters.base import PromptRequest
from pizhi.services.run_store import RunRecord


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    project_root: Path
    prompt_request: PromptRequest
    target: str
    route_name: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    run_id: str
    run_dir: Path
    status: str
    record: RunRecord


class ExecutionBackend(Protocol):
    backend_name: str

    def execute(
        self,
        request: ExecutionRequest,
        *,
        backend_config: object | None = None,
    ) -> ExecutionResult: ...
