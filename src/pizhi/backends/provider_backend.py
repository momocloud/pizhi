from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import urlopen

from pizhi.adapters.openai_compatible import build_http_request
from pizhi.adapters.openai_compatible import parse_response
from pizhi.adapters.provider_base import ProviderRequest
from pizhi.adapters.provider_base import ProviderResponse
from pizhi.backends.base import ExecutionRequest
from pizhi.backends.base import ExecutionResult
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.paths import project_paths
from pizhi.services.run_store import RunStore
from pizhi.services.write_candidate_validation import validate_write_candidate


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


class ProviderExecutionBackend:
    backend_name = "provider"

    def __init__(self, *, adapter_builder=None) -> None:
        self._adapter_builder = build_provider_adapter if adapter_builder is None else adapter_builder

    def execute(
        self,
        request: ExecutionRequest,
        *,
        backend_config: object | None = None,
    ) -> ExecutionResult:
        provider_config = self._resolve_provider_config(
            request.project_root,
            route_name=request.route_name,
            backend_config=backend_config,
        )
        api_key = _load_api_key(provider_config.api_key_env)
        adapter = self._adapter_builder(provider_config.provider)
        provider_request = ProviderRequest(
            model=provider_config.model,
            base_url=provider_config.base_url,
            api_key=api_key,
            prompt_text=request.prompt_request.prompt_text,
        )
        store = RunStore(project_paths(request.project_root).runs_dir)
        metadata = {
            **request.prompt_request.metadata,
            "backend": self.backend_name,
            "provider": provider_config.provider,
            "model": provider_config.model,
            "base_url": provider_config.base_url,
        }

        try:
            response = adapter.execute(provider_request)
        except Exception as exc:
            record = store.write_failure(
                command=request.prompt_request.command_name,
                target=request.target,
                prompt_text=request.prompt_request.prompt_text,
                error_text=str(exc),
                status="provider_failed",
                metadata=metadata,
                referenced_files=request.prompt_request.referenced_files,
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
                command=request.prompt_request.command_name,
                target=request.target,
                prompt_text=request.prompt_request.prompt_text,
                raw_payload=response.raw_payload,
                normalized_text=response.content_text,
                error_text=str(exc),
                status="normalize_failed",
                metadata=metadata,
                referenced_files=request.prompt_request.referenced_files,
            )
            return ExecutionResult(
                run_id=record.run_id,
                run_dir=record.run_dir,
                status="normalize_failed",
                record=record,
            )

        if request.prompt_request.command_name == "write":
            try:
                validate_write_candidate(normalized_text)
            except ValueError as exc:
                record = store.write_failure(
                    command=request.prompt_request.command_name,
                    target=request.target,
                    prompt_text=request.prompt_request.prompt_text,
                    raw_payload=response.raw_payload,
                    normalized_text=normalized_text,
                    error_text=str(exc),
                    status="normalize_failed",
                    metadata=metadata,
                    referenced_files=request.prompt_request.referenced_files,
                )
                return ExecutionResult(
                    run_id=record.run_id,
                    run_dir=record.run_dir,
                    status="normalize_failed",
                    record=record,
                )

        record = store.write_success(
            command=request.prompt_request.command_name,
            target=request.target,
            prompt_text=request.prompt_request.prompt_text,
            raw_payload=response.raw_payload,
            normalized_text=normalized_text,
            metadata=metadata,
            referenced_files=request.prompt_request.referenced_files,
        )
        return ExecutionResult(
            run_id=record.run_id,
            run_dir=record.run_dir,
            status="succeeded",
            record=record,
        )

    def _resolve_provider_config(
        self,
        project_root: Path,
        *,
        route_name: str | None = None,
        backend_config: object | None = None,
    ) -> ProviderSection:
        if backend_config is not None:
            if not isinstance(backend_config, ProviderSection):
                raise TypeError("provider backend override must be a ProviderSection")
            return backend_config

        config = load_config(project_paths(project_root).config_file)
        if config.provider is None:
            raise ValueError("provider is not configured")
        if route_name is not None:
            return config.provider.resolve_route_config(route_name)
        return config.provider


def _load_api_key(env_name: str) -> str:
    api_key = os.environ.get(env_name)
    if not api_key:
        raise ValueError(f"{env_name} is not set")
    return api_key


def _normalize_provider_content(content_text: str) -> str:
    if not content_text.strip():
        raise ValueError("provider response did not contain text content")
    return content_text
