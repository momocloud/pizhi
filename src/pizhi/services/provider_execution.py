from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from urllib.request import urlopen

from pizhi.adapters.base import PromptRequest
from pizhi.adapters.openai_compatible import build_http_request
from pizhi.adapters.openai_compatible import parse_response
from pizhi.adapters.provider_base import ProviderRequest
from pizhi.adapters.provider_base import ProviderResponse
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.paths import project_paths
from pizhi.services.run_store import RunRecord
from pizhi.services.run_store import RunStore


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    run_id: str
    run_dir: Path
    status: str
    record: RunRecord


class OpenAICompatibleAdapter:
    def execute(self, request: ProviderRequest) -> ProviderResponse:
        http_request = build_http_request(request)
        with urlopen(http_request) as response:
            payload = response.read().decode("utf-8")
        return parse_response(json.loads(payload))


def build_provider_adapter(provider_name: str):
    if provider_name == "openai_compatible":
        return OpenAICompatibleAdapter()
    raise ValueError(f"unsupported provider: {provider_name}")


def execute_prompt_request(
    project_root: Path,
    request: PromptRequest,
    target: str,
    route_name: str | None = None,
    provider_config: ProviderSection | None = None,
) -> ExecutionResult:
    provider_config = provider_config or _load_provider_config(project_root, route_name=route_name)
    api_key = _load_api_key(provider_config.api_key_env)
    adapter = build_provider_adapter(provider_config.provider)
    provider_request = ProviderRequest(
        model=provider_config.model,
        base_url=provider_config.base_url,
        api_key=api_key,
        prompt_text=request.prompt_text,
    )
    store = RunStore(project_paths(project_root).runs_dir)
    metadata = {
        **request.metadata,
        "provider": provider_config.provider,
        "model": provider_config.model,
        "base_url": provider_config.base_url,
    }

    try:
        response = adapter.execute(provider_request)
    except Exception as exc:
        record = store.write_failure(
            command=request.command_name,
            target=target,
            prompt_text=request.prompt_text,
            error_text=str(exc),
            status="provider_failed",
            metadata=metadata,
            referenced_files=request.referenced_files,
        )
        return ExecutionResult(
            run_id=record.run_id,
            run_dir=record.run_dir,
            status="provider_failed",
            record=record,
        )

    try:
        normalized_text = _normalize_provider_content(response.content_text)
    except ValueError as exc:
        record = store.write_failure(
            command=request.command_name,
            target=target,
            prompt_text=request.prompt_text,
            raw_payload=response.raw_payload,
            normalized_text=response.content_text,
            error_text=str(exc),
            status="normalize_failed",
            metadata=metadata,
            referenced_files=request.referenced_files,
        )
        return ExecutionResult(
            run_id=record.run_id,
            run_dir=record.run_dir,
            status="normalize_failed",
            record=record,
        )

    record = store.write_success(
        command=request.command_name,
        target=target,
        prompt_text=request.prompt_text,
        raw_payload=response.raw_payload,
        normalized_text=normalized_text,
        metadata=metadata,
        referenced_files=request.referenced_files,
    )
    return ExecutionResult(
        run_id=record.run_id,
        run_dir=record.run_dir,
        status="succeeded",
        record=record,
    )


def _load_provider_config(project_root: Path, route_name: str | None = None) -> ProviderSection:
    config = load_config(project_paths(project_root).config_file)
    if config.provider is None:
        raise ValueError("provider is not configured")
    if route_name is not None:
        return config.provider.resolve_route_config(route_name)
    return config.provider


def _load_api_key(env_name: str) -> str:
    import os

    api_key = os.environ.get(env_name)
    if not api_key:
        raise ValueError(f"{env_name} is not set")
    return api_key


def _normalize_provider_content(content_text: str) -> str:
    if not content_text.strip():
        raise ValueError("provider response did not contain text content")
    return content_text
