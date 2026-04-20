from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from pizhi.domain.agent_extensions import AgentSpec
from pizhi.services.agent_registry import AgentRegistry
from pizhi.services.agent_extensions import AgentExecutionResult
from pizhi.services.agent_extensions import NO_AI_REVIEW_ISSUES_MESSAGE
from pizhi.services.agent_extensions import execute_agent_spec
from pizhi.services.agent_extensions import render_agent_execution_section
from pizhi.services.agent_extensions import render_extension_runtime_failure_section
from pizhi.services.agent_extensions import render_extension_setup_failure_section
from pizhi.services.run_store import RunRecord
from pizhi.services.run_store import RunStore


@dataclass
class FakeExecution:
    status: str = "succeeded"
    run_id: str | None = None
    record: RunRecord | None = None


def _write_success_record(runs_dir: Path, normalized_text: str) -> RunRecord:
    store = RunStore(runs_dir)
    return store.write_success(
        command="review-agent",
        target="ch002",
        prompt_text="prompt",
        raw_payload={"id": "resp_test"},
        normalized_text=normalized_text,
        metadata={},
        referenced_files=[],
    )


def _write_failure_record(runs_dir: Path, *, status: str, error_text: str) -> RunRecord:
    store = RunStore(runs_dir)
    return store.write_failure(
        command="review-agent",
        target="ch002",
        prompt_text="prompt",
        error_text=error_text,
        status=status,
        metadata={},
        referenced_files=[],
    )


def test_agent_registry_filters_enabled_agents_by_kind_and_scope():
    registry = AgentRegistry(
        [
            AgentSpec(
                agent_id="critique.chapter",
                kind="review",
                description="chapter critique agent",
                enabled=True,
                target_scope="chapter",
                prompt_template="Review the chapter for pacing drift.",
            ),
            AgentSpec(
                agent_id="critique.disabled",
                kind="review",
                description="disabled chapter critique agent",
                enabled=False,
                target_scope="chapter",
                prompt_template="Review the chapter for pacing drift.",
            ),
            AgentSpec(
                agent_id="archive.audit",
                kind="maintenance",
                description="archive audit agent",
                enabled=True,
                target_scope="project",
                prompt_template="Audit the maintenance summary for missed archive work.",
            ),
        ]
    )

    chapter_review_agents = registry.iter_enabled(kind="review", target_scope="chapter")

    assert [agent.agent_id for agent in chapter_review_agents] == ["critique.chapter"]


def test_agent_spec_rejects_invalid_kind_and_target_scope():
    with pytest.raises(ValueError, match="unknown agent kind"):
        AgentSpec(
            agent_id="bad.kind",
            kind="unknown",  # type: ignore[arg-type]
            description="invalid",
            enabled=True,
            target_scope="chapter",
            prompt_template="noop",
        )

    with pytest.raises(ValueError, match="unknown agent target scope"):
        AgentSpec(
            agent_id="bad.scope",
            kind="review",
            description="invalid",
            enabled=True,
            target_scope="anywhere",  # type: ignore[arg-type]
            prompt_template="noop",
        )


def test_execute_agent_spec_treats_no_issues_marker_as_success(monkeypatch, initialized_project):
    spec = AgentSpec(
        agent_id="critique.chapter",
        kind="review",
        description="chapter critique agent",
        enabled=True,
        target_scope="chapter",
        prompt_template="Review this chapter for pacing drift.",
    )
    captured: dict[str, str] = {}
    record = _write_success_record(initialized_project / ".pizhi" / "cache" / "runs", NO_AI_REVIEW_ISSUES_MESSAGE)

    def fake_execute_prompt_request(project_root, request, target, route_name=None, provider_config=None):
        captured["prompt_text"] = request.prompt_text
        return FakeExecution(run_id=record.run_id, record=record)

    monkeypatch.setattr("pizhi.services.agent_extensions.execute_prompt_request", fake_execute_prompt_request)

    result = execute_agent_spec(
        initialized_project,
        spec,
        target="ch002",
        context_markdown="context",
    )

    assert result.status == "succeeded"
    assert result.summary == "No issues found"
    assert result.issues == []
    assert NO_AI_REVIEW_ISSUES_MESSAGE.strip() in captured["prompt_text"]
    assert "### 问题 1" in captured["prompt_text"]


def test_execute_agent_spec_normalizes_successful_issue_payload(monkeypatch, initialized_project):
    spec = AgentSpec(
        agent_id="critique.chapter",
        kind="review",
        description="chapter critique agent",
        enabled=True,
        target_scope="chapter",
        prompt_template="Review this chapter for pacing drift.",
    )
    record = _write_success_record(
        initialized_project / ".pizhi" / "cache" / "runs",
        """\
### 问题 1
- **类别**：人物一致性
- **严重度**：高
- **描述**：沈轩前后动机冲突。
- **证据**：ch002 的动作与前文不一致。
- **建议修法**：补一段心理铺垫。
""",
    )

    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_prompt_request",
        lambda *args, **kwargs: FakeExecution(run_id=record.run_id, record=record),
    )

    result = execute_agent_spec(
        initialized_project,
        spec,
        target="ch002",
        context_markdown="context",
    )

    assert result.status == "succeeded"
    assert result.summary == "1 issue(s) found"
    assert len(result.issues) == 1
    assert result.issues[0].category == "人物一致性"


def test_execute_agent_spec_allows_maintenance_issue_categories(monkeypatch, initialized_project):
    spec = AgentSpec(
        agent_id="archive.audit",
        kind="maintenance",
        description="archive audit agent",
        enabled=True,
        target_scope="project",
        prompt_template="Audit maintenance output for archive issues.",
    )
    record = _write_success_record(
        initialized_project / ".pizhi" / "cache" / "runs",
        """\
### 问题 1
- **类别**：Archive
- **严重度**：中
- **描述**：归档块缺少章节边界说明。
- **证据**：timeline_ch001-050.md 只有标题，没有收口说明。
- **建议修法**：补一行 archive boundary note。
""",
    )

    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_prompt_request",
        lambda *args, **kwargs: FakeExecution(run_id=record.run_id, record=record),
    )

    result = execute_agent_spec(
        initialized_project,
        spec,
        target="project",
        context_markdown="context",
    )

    assert result.status == "succeeded"
    assert len(result.issues) == 1
    assert result.issues[0].category == "Archive"


def test_execute_agent_spec_converts_provider_failure_into_failed_result(monkeypatch, initialized_project):
    spec = AgentSpec(
        agent_id="critique.chapter",
        kind="review",
        description="chapter critique agent",
        enabled=True,
        target_scope="chapter",
        prompt_template="Review this chapter for pacing drift.",
    )

    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_prompt_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider down")),
    )

    result = execute_agent_spec(initialized_project, spec, target="project", context_markdown="context")

    assert result.status == "failed"
    assert result.failure_reason == "provider down"


def test_execute_agent_spec_converts_non_succeeded_execution_into_failed_result(
    monkeypatch, initialized_project
):
    spec = AgentSpec(
        agent_id="critique.chapter",
        kind="review",
        description="chapter critique agent",
        enabled=True,
        target_scope="chapter",
        prompt_template="Review this chapter for pacing drift.",
    )
    record = _write_failure_record(
        initialized_project / ".pizhi" / "cache" / "runs",
        status="provider_failed",
        error_text="provider down",
    )

    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_prompt_request",
        lambda *args, **kwargs: FakeExecution(status="provider_failed", run_id=record.run_id, record=record),
    )

    result = execute_agent_spec(
        initialized_project,
        spec,
        target="project",
        context_markdown="context",
    )

    assert result.status == "failed"
    assert result.failure_reason == "provider down"


def test_execute_agent_spec_converts_parse_failure_into_failed_result(monkeypatch, initialized_project):
    spec = AgentSpec(
        agent_id="critique.chapter",
        kind="review",
        description="chapter critique agent",
        enabled=True,
        target_scope="chapter",
        prompt_template="Review this chapter for pacing drift.",
    )
    record = _write_success_record(initialized_project / ".pizhi" / "cache" / "runs", "not review markdown")

    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_prompt_request",
        lambda *args, **kwargs: FakeExecution(run_id=record.run_id, record=record),
    )

    result = execute_agent_spec(
        initialized_project,
        spec,
        target="project",
        context_markdown="context",
    )

    assert result.status == "failed"
    assert result.failure_reason == "ai review markdown must start with an issue block"
    run_store = RunStore(initialized_project / ".pizhi" / "cache" / "runs")
    persisted = run_store.load(record.run_id)
    assert persisted.status == "failed"
    assert persisted.error_path.read_text(encoding="utf-8").strip() == "ai review markdown must start with an issue block"


def test_render_extension_failure_sections_escape_heading_like_error_text():
    setup_section = render_extension_setup_failure_section("trace\n## setup heading\nmore")
    runtime_section = render_extension_runtime_failure_section(
        "critique.chapter",
        "trace\n## runtime heading\nmore",
    )

    assert "\n## setup heading\n" not in setup_section.body
    assert "\n## runtime heading\n" not in runtime_section.body
    assert "> ## setup heading" in setup_section.body
    assert "> ## runtime heading" in runtime_section.body


def test_render_agent_execution_section_quotes_heading_like_failure_reason():
    section = render_agent_execution_section(
        AgentExecutionResult(
            agent_id="critique.chapter",
            kind="review",
            status="failed",
            summary="Execution failed",
            issues=[],
            suggestions=[],
            failure_reason="trace\n## nested heading\nmore",
            run_id="run_ext",
        )
    )

    assert "\n## nested heading\n" not in section.body
    assert "> ## nested heading" in section.body
    assert "- Run ID: run_ext" in section.body
