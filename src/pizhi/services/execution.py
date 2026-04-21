from __future__ import annotations

from pathlib import Path

from pizhi.adapters.base import PromptRequest
from pizhi.backends.base import ExecutionRequest
from pizhi.backends.base import ExecutionResult
from pizhi.backends.provider_backend import ProviderExecutionBackend
from pizhi.core.config import load_config
from pizhi.core.paths import project_paths


def execute_prompt_request(
    project_root: Path,
    request: PromptRequest,
    target: str,
    route_name: str | None = None,
) -> ExecutionResult:
    config = load_config(project_paths(project_root).config_file)
    backend_name = config.execution.backend
    backend = _build_execution_backend(backend_name)
    return backend.execute(
        ExecutionRequest(
            project_root=project_root,
            prompt_request=request,
            target=target,
            route_name=route_name,
        )
    )


def _build_execution_backend(backend_name: str):
    if backend_name == "provider":
        return ProviderExecutionBackend()
    raise ValueError(f"unsupported execution backend: {backend_name}")
