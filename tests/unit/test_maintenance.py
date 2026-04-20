from __future__ import annotations

from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.services.archive_service import ArchiveResult
from pizhi.domain.agent_extensions import AgentSpec
from pizhi.domain.ai_review import AIReviewIssue
from pizhi.services.agent_extensions import AgentExecutionResult
from pizhi.services.agent_registry import AgentRegistry
from pizhi.services.maintenance import MaintenanceFinding
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.maintenance import format_maintenance_summary
from pizhi.services.maintenance import format_checkpoint_maintenance
from pizhi.services.maintenance import run_after_write
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


def configure_chapter_scoped_maintenance_agent(initialized_project, *, agent_id: str = "archive.chapter") -> None:
    config_path = initialized_project / ".pizhi" / "config.yaml"
    config = load_config(config_path)
    config.agents = [
        AgentSpec(
            agent_id=agent_id,
            kind="maintenance",
            description="Chapter-scoped maintenance agent.",
            enabled=True,
            target_scope="chapter",
            prompt_template="This should not run from maintenance.",
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


def test_run_full_maintenance_preserves_actionable_maintenance_issue_details(initialized_project, monkeypatch):
    configure_maintenance_agent(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_agent_spec",
        lambda *args, **kwargs: AgentExecutionResult(
            agent_id="archive.audit",
            kind="maintenance",
            status="succeeded",
            summary="1 issue(s) found",
            issues=[
                AIReviewIssue(
                    category="Archive",
                    severity="中",
                    description="归档块缺少章节边界说明。",
                    evidence="timeline_ch001-050.md 没有收口说明。",
                    suggestion="补一行 archive boundary note。",
                )
            ],
            suggestions=["补一行 archive boundary note。"],
            failure_reason=None,
            run_id="run_123",
        ),
    )

    result = run_full_maintenance(initialized_project)
    summary = format_maintenance_summary(result)

    assert "归档块缺少章节边界说明。" in summary
    assert "补一行 archive boundary note。" in summary


def test_run_full_maintenance_ignores_successful_extension_without_issues(initialized_project, monkeypatch):
    configure_maintenance_agent(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_agent_spec",
        lambda *args, **kwargs: AgentExecutionResult(
            agent_id="archive.audit",
            kind="maintenance",
            status="succeeded",
            summary="No issues found",
            issues=[],
            suggestions=[],
            failure_reason=None,
            run_id="run_123",
        ),
    )

    result = run_full_maintenance(initialized_project)

    assert all(finding.category != "Maintenance agent" for finding in result.findings)


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


def test_run_full_maintenance_ignores_chapter_scoped_maintenance_agents(initialized_project, monkeypatch):
    configure_chapter_scoped_maintenance_agent(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_agent_spec",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("chapter-scoped maintenance agents must not run")),
    )

    result = run_full_maintenance(initialized_project)

    assert all(finding.category != "Maintenance agent" for finding in result.findings)


def test_run_after_write_appends_extension_findings_by_default(initialized_project, monkeypatch):
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

    result = run_after_write(initialized_project)

    assert any(finding.category == "Maintenance agent" for finding in result.findings)


def test_run_full_maintenance_can_skip_maintenance_agents_when_extensions_disabled(initialized_project, monkeypatch):
    configure_maintenance_agent(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.maintenance.load_agent_registry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("extensions should stay disabled")),
    )

    result = run_full_maintenance(initialized_project, include_extensions=False)

    assert all(finding.category != "Maintenance agent" for finding in result.findings)


def test_format_checkpoint_maintenance_includes_maintenance_agent_findings():
    result = MaintenanceResult(
        synopsis_review=None,
        archive_result=ArchiveResult(findings=[]),
        findings=[
            MaintenanceFinding(
                category="Maintenance agent",
                detail="archive.audit: synopsis-extension finding",
            )
        ],
    )

    checkpoint_summary = format_checkpoint_maintenance([(3, result)])

    assert "Maintenance agent" in checkpoint_summary
    assert "archive.audit: synopsis-extension finding" in checkpoint_summary
