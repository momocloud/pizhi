from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from pizhi.adapters.provider_base import ProviderResponse
from pizhi.core.config import AgentBackendSection
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.services.brainstorm_service import BrainstormService
from pizhi.services.provider_execution import execute_prompt_request
from pizhi.services.maintenance import MaintenanceFinding
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.run_store import RunStore
from pizhi.services.write_service import WriteService


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
        brainstorm_model="gpt-5.4-brainstorm",
        outline_model="gpt-5.4-outline",
        write_model="gpt-5.4-write",
        review_model="gpt-5.4-mini",
    )
    save_config(project_root / ".pizhi" / "config.yaml", config)


def test_execute_prompt_request_requires_provider_config(initialized_project):
    request = BrainstormService(initialized_project).build_prompt_request()
    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"

    with pytest.raises(ValueError, match="provider is not configured"):
        execute_prompt_request(initialized_project, request, target="project")

    assert not runs_dir.exists()


def test_execute_prompt_request_requires_provider_api_key_env(initialized_project):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        execute_prompt_request(initialized_project, request, target="project")

    assert not runs_dir.exists()


def test_execute_prompt_request_uses_explicit_provider_config(initialized_project, monkeypatch):
    request = BrainstormService(initialized_project).build_prompt_request()
    config = load_config(initialized_project / ".pizhi" / "config.yaml")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="project-model",
        base_url="https://project.example/v1",
        api_key_env="PROJECT_API_KEY",
    )
    save_config(initialized_project / ".pizhi" / "config.yaml", config)
    explicit_provider_config = ProviderSection(
        provider="openai_compatible",
        model="override-model",
        base_url="https://override.example/v1",
        api_key_env="OVERRIDE_API_KEY",
    )
    captured: dict[str, object] = {}

    class RecordingAdapter:
        def execute(self, provider_request):
            captured["provider_request"] = provider_request
            return ProviderResponse(
                raw_payload={"id": "resp_test"},
                content_text="## synopsis\n...",
            )

    monkeypatch.setenv("OVERRIDE_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RecordingAdapter(),
    )

    result = execute_prompt_request(
        initialized_project,
        request,
        target="project",
        provider_config=explicit_provider_config,
    )

    provider_request = captured["provider_request"]
    assert result.status == "succeeded"
    assert provider_request.model == "override-model"
    assert provider_request.base_url == "https://override.example/v1"
    assert provider_request.api_key == "secret"


def test_execute_prompt_request_uses_route_config_for_command_family(initialized_project, monkeypatch):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    captured: dict[str, object] = {}

    class RecordingAdapter:
        def execute(self, provider_request):
            captured["provider_request"] = provider_request
            return ProviderResponse(
                raw_payload={"id": "resp_test"},
                content_text="## synopsis\n...",
            )

    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RecordingAdapter(),
    )

    result = execute_prompt_request(
        initialized_project,
        request,
        target="project",
        route_name="brainstorm",
    )

    provider_request = captured["provider_request"]
    assert result.status == "succeeded"
    assert provider_request.model == "gpt-5.4-brainstorm"
    assert result.record.metadata["model"] == "gpt-5.4-brainstorm"


def test_execute_prompt_request_prefers_explicit_provider_config_over_route_name(
    initialized_project, monkeypatch
):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    explicit_provider_config = ProviderSection(
        provider="openai_compatible",
        model="override-model",
        base_url="https://override.example/v1",
        api_key_env="OVERRIDE_API_KEY",
    )
    captured: dict[str, object] = {}

    class RecordingAdapter:
        def execute(self, provider_request):
            captured["provider_request"] = provider_request
            return ProviderResponse(
                raw_payload={"id": "resp_test"},
                content_text="## synopsis\n...",
            )

    monkeypatch.setenv("OVERRIDE_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RecordingAdapter(),
    )

    result = execute_prompt_request(
        initialized_project,
        request,
        target="project",
        provider_config=explicit_provider_config,
        route_name="brainstorm",
    )

    provider_request = captured["provider_request"]
    assert result.status == "succeeded"
    assert provider_request.model == "override-model"
    assert result.record.metadata["model"] == "override-model"


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
    assert result.record.metadata["backend"] == "provider"
    assert result.run_dir.joinpath("normalized.md").read_text(encoding="utf-8").startswith("##")


def test_execute_prompt_request_routes_agent_backend_through_compatibility_facade(
    initialized_project, monkeypatch
):
    request = BrainstormService(initialized_project).build_prompt_request()
    config = load_config(initialized_project / ".pizhi" / "config.yaml")
    config.execution.backend = "agent"
    config.execution.agent = AgentBackendSection(
        agent_backend="opencode",
        agent_command="opencode",
        agent_args=["run"],
    )
    save_config(initialized_project / ".pizhi" / "config.yaml", config)

    def fake_run(command, *, cwd, capture_output, text, encoding):
        Path(cwd, "agent_output.md").write_text("## synopsis\n...\n", encoding="utf-8")
        return CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_run)

    result = execute_prompt_request(
        initialized_project,
        request,
        target="project",
        route_name="brainstorm",
    )

    assert result.status == "succeeded"
    assert result.record.metadata["backend"] == "agent"
    assert result.record.metadata["agent_backend"] == "opencode"


def test_execute_prompt_request_persists_normalize_failed_when_provider_returns_no_text(
    initialized_project, monkeypatch
):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StubAdapter(""),
    )

    result = execute_prompt_request(initialized_project, request, target="project")
    loaded = RunStore(initialized_project / ".pizhi" / "cache" / "runs").load(result.run_id)

    assert result.status == "normalize_failed"
    assert result.record.status == "normalize_failed"
    assert loaded.status == "normalize_failed"
    assert loaded.raw_path.exists()
    assert loaded.normalized_path.exists()
    assert loaded.normalized_path.read_text(encoding="utf-8") == ""
    assert loaded.error_path.read_text(encoding="utf-8").strip() == "provider response did not contain text content"


def test_write_service_apply_response_returns_maintenance_result(initialized_project, monkeypatch):
    service = WriteService(initialized_project)
    chapter_result = object()
    maintenance_result = MaintenanceResult(
        synopsis_review=None,
        archive_result=None,
        findings=[MaintenanceFinding(category="Archive", detail="rotated")],
    )
    calls: list[tuple[str, object]] = []

    def _apply(project_root, *, chapter_number, raw_response):
        calls.append(("apply", project_root, chapter_number, raw_response))
        return chapter_result

    def _maintain(project_root):
        calls.append(("maintain", project_root))
        return maintenance_result

    monkeypatch.setattr("pizhi.services.write_service.apply_chapter_response", _apply)
    monkeypatch.setattr("pizhi.services.write_service.run_after_write", _maintain)

    result = service.apply_response(7, "raw response")

    assert result.chapter_result is chapter_result
    assert result.maintenance_result is maintenance_result
    assert calls == [
        ("apply", initialized_project, 7, "raw response"),
        ("maintain", initialized_project),
    ]
