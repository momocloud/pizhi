from __future__ import annotations

from pathlib import Path

from pizhi.adapters.base import PromptRequest
from pizhi.backends.base import ExecutionResult
from pizhi.backends.provider_backend import build_provider_adapter as _build_provider_adapter
from pizhi.core.config import ProviderSection
from pizhi.services.execution import execute_prompt_request as _execute_prompt_request


build_provider_adapter = _build_provider_adapter


def execute_prompt_request(
    project_root: Path,
    request: PromptRequest,
    target: str,
    route_name: str | None = None,
    provider_config: ProviderSection | None = None,
) -> ExecutionResult:
    return _execute_prompt_request(
        project_root,
        request,
        target,
        route_name=route_name,
        provider_config=provider_config,
        provider_adapter_builder=build_provider_adapter,
    )
