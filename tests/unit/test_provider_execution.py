from __future__ import annotations

from dataclasses import dataclass

import pytest

from pizhi.adapters.provider_base import ProviderResponse
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.services.brainstorm_service import BrainstormService
from pizhi.services.provider_execution import execute_prompt_request
from pizhi.services.run_store import RunStore


@dataclass
class FailingAdapter:
    error_message: str = "provider request failed"

    def execute(self, request):
        raise RuntimeError(self.error_message)


@dataclass
class StubAdapter:
    content_text: str

    def execute(self, request):
        return ProviderResponse(
            raw_payload={"id": "resp_test"},
            content_text=self.content_text,
        )


def _configure_provider(project_root) -> None:
    config = load_config(project_root / ".pizhi" / "config.yaml")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    save_config(project_root / ".pizhi" / "config.yaml", config)


def test_execute_prompt_request_requires_provider_config(initialized_project):
    request = BrainstormService(initialized_project).build_prompt_request()

    with pytest.raises(ValueError, match="provider is not configured"):
        execute_prompt_request(initialized_project, request, target="project")


def test_execute_prompt_request_requires_provider_api_key_env(initialized_project):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        execute_prompt_request(initialized_project, request, target="project")


def test_execute_prompt_request_persists_failed_provider_run(initialized_project, monkeypatch):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: FailingAdapter(),
    )

    result = execute_prompt_request(initialized_project, request, target="ch001")
    loaded = RunStore(initialized_project / ".pizhi" / "cache" / "runs").load(result.run_id)

    assert result.status == "provider_failed"
    assert result.record.status == "provider_failed"
    assert loaded.status == "provider_failed"
    assert result.run_dir.joinpath("error.txt").exists()


def test_execute_prompt_request_persists_normalized_success(initialized_project, monkeypatch):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StubAdapter("## synopsis\n..."),
    )

    result = execute_prompt_request(initialized_project, request, target="project")

    assert result.status == "succeeded"
    assert result.run_dir.joinpath("normalized.md").read_text(encoding="utf-8").startswith("##")
