from __future__ import annotations

from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.domain.agent_extensions import AgentSpec
from pizhi.services.agent_extensions import AgentExecutionResult
from pizhi.services.agent_registry import AgentRegistry
from pizhi.services.maintenance import format_maintenance_summary
from pizhi.services.maintenance import run_full_maintenance


def configure_maintenance_agent(initialized_project, *, agent_id: str = "archive.audit") -> None:
    config_path = initialized_project / ".pizhi" / "config.yaml"
    config = load_config(config_path)
    config.agents = [
        AgentSpec(
            agent_id=agent_id,
            kind="maintenance",
            description="Extension maintenance agent.",
            enabled=True,
            target_scope="project",
            prompt_template="Audit the maintenance results.",
        )
    ]
    save_config(config_path, config)


def test_run_full_maintenance_appends_extension_findings(initialized_project, monkeypatch):
    configure_maintenance_agent(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_agent_spec",
        lambda *args, **kwargs: AgentExecutionResult(
            agent_id="archive.audit",
            kind="maintenance",
            status="succeeded",
            summary="archive summary",
            issues=[],
            suggestions=["rotate timeline archive"],
            failure_reason=None,
            run_id="run_123",
        ),
    )

    result = run_full_maintenance(initialized_project)

    assert any(finding.category == "Maintenance agent" for finding in result.findings)
    assert "archive.audit" in format_maintenance_summary(result)


def test_run_full_maintenance_records_registry_load_failures_as_findings(initialized_project, monkeypatch):
    monkeypatch.setattr(
        "pizhi.services.maintenance.load_agent_registry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid agent config")),
    )

    result = run_full_maintenance(initialized_project)

    assert any(
        finding.category == "Maintenance agent" and "invalid agent config" in finding.detail
        for finding in result.findings
    )


def test_run_full_maintenance_records_runtime_failures_as_findings(initialized_project, monkeypatch):
    monkeypatch.setattr(
        "pizhi.services.maintenance.load_agent_registry",
        lambda *_args, **_kwargs: AgentRegistry(
            [
                AgentSpec(
                    agent_id="archive.audit",
                    kind="maintenance",
                    description="Extension maintenance agent.",
                    enabled=True,
                    target_scope="project",
                    prompt_template="Audit the maintenance results.",
                )
            ]
        ),
    )
    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_agent_spec",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("agent runtime boom")),
    )

    result = run_full_maintenance(initialized_project)

    assert any(
        finding.category == "Maintenance agent" and "agent runtime boom" in finding.detail
        for finding in result.findings
    )
