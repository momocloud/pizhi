from __future__ import annotations

import pytest

from pizhi.core.config import AgentBackendSection
from pizhi.core.config import ExecutionConfig
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.services.brainstorm_service import BrainstormService
from pizhi.services.execution import execute_prompt_request
from tests.unit.test_provider_execution import StubAdapter
from tests.unit.test_provider_execution import _configure_provider


def test_execute_prompt_request_selects_provider_backend_from_execution_config(
    initialized_project, monkeypatch
):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.backends.provider_backend.build_provider_adapter",
        lambda *_: StubAdapter("## synopsis\n..."),
    )

    result = execute_prompt_request(
        initialized_project,
        request,
        target="project",
        route_name="brainstorm",
    )

    assert result.status == "succeeded"
    assert result.record.metadata["backend"] == "provider"
    assert result.record.metadata["model"] == "gpt-5.4-brainstorm"


def test_execute_prompt_request_rejects_unknown_backend(initialized_project):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    config_path = initialized_project / ".pizhi" / "config.yaml"
    config = load_config(config_path)
    config.execution = ExecutionConfig(backend="unknown", provider=config.provider, agent=None)
    save_config(config_path, config)

    with pytest.raises(ValueError, match="unsupported execution backend"):
        execute_prompt_request(initialized_project, request, target="project")


def test_execute_prompt_request_selects_agent_backend_from_execution_config(
    initialized_project, monkeypatch
):
    request = BrainstormService(initialized_project).build_prompt_request()
    config_path = initialized_project / ".pizhi" / "config.yaml"
    config = load_config(config_path)
    config.execution = ExecutionConfig(
        backend="agent",
        provider=None,
        agent=AgentBackendSection(
            agent_backend="opencode",
            agent_command="opencode",
            agent_args=["run"],
        ),
    )
    save_config(config_path, config)

    def fake_run(command, *, cwd, capture_output, text, encoding):
        from pathlib import Path
        from subprocess import CompletedProcess

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
