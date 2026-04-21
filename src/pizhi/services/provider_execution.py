from __future__ import annotations

from pathlib import Path

from pizhi.adapters.base import PromptRequest
from pizhi.backends.base import ExecutionRequest
from pizhi.backends.base import ExecutionResult
from pizhi.backends.opencode_backend import OpencodeExecutionBackend
from pizhi.backends.provider_backend import OpenAICompatibleAdapter
from pizhi.backends.provider_backend import ProviderExecutionBackend
from pizhi.backends.provider_backend import build_provider_adapter as _build_provider_adapter
from pizhi.core.config import load_config
from pizhi.core.config import ProviderSection
from pizhi.core.paths import project_paths


build_provider_adapter = _build_provider_adapter


def execute_prompt_request(
    project_root: Path,
    request: PromptRequest,
    target: str,
    route_name: str | None = None,
    provider_config: ProviderSection | None = None,
) -> ExecutionResult:
    if provider_config is None:
        config = load_config(project_paths(project_root).config_file)
        if config.execution.backend == "agent":
            if config.execution.agent is None:
                raise ValueError("agent backend is not configured")
            return OpencodeExecutionBackend().execute(
                ExecutionRequest(
                    project_root=project_root,
                    prompt_request=request,
                    target=target,
                    route_name=route_name,
                ),
                backend_config=config.execution.agent,
            )
        if config.execution.backend != "provider":
            raise ValueError(f"unsupported execution backend: {config.execution.backend}")

    backend = ProviderExecutionBackend(adapter_builder=build_provider_adapter)
    return backend.execute(
        ExecutionRequest(
            project_root=project_root,
            prompt_request=request,
            target=target,
            route_name=route_name,
        ),
        backend_config=provider_config,
    )
