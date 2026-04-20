from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from pizhi.domain.agent_extensions import AgentSpec
from pizhi.services.agent_extensions import execute_agent_spec


@dataclass
class FakeRecord:
    normalized_path: Path
    error_path: Path


@dataclass
class FakeExecution:
    status: str = "succeeded"
    run_id: str = "run-test"
    record: FakeRecord | None = None


def _write_record(tmp_path: Path, normalized_text: str, error_text: str = "") -> FakeRecord:
    normalized_path = tmp_path / "normalized.md"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(normalized_text, encoding="utf-8")
    error_path = tmp_path / "error.txt"
    error_path.write_text(error_text, encoding="utf-8")
    return FakeRecord(normalized_path=normalized_path, error_path=error_path)


def test_execute_agent_spec_normalizes_successful_issue_payload(monkeypatch, initialized_project):
    spec = AgentSpec(
        agent_id="critique.chapter",
        kind="review",
        description="chapter critique agent",
        enabled=True,
        target_scope="chapter",
        prompt_template="Review this chapter for pacing drift.",
    )
    record = _write_record(
        initialized_project / ".pizhi" / "cache",
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
        lambda *args, **kwargs: FakeExecution(record=record),
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
    record = _write_record(initialized_project / ".pizhi" / "cache", "")

    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_prompt_request",
        lambda *args, **kwargs: FakeExecution(status="provider_failed", record=record),
    )

    result = execute_agent_spec(
        initialized_project,
        spec,
        target="project",
        context_markdown="context",
    )

    assert result.status == "failed"
    assert result.failure_reason == "provider_failed"


def test_execute_agent_spec_converts_parse_failure_into_failed_result(monkeypatch, initialized_project):
    spec = AgentSpec(
        agent_id="critique.chapter",
        kind="review",
        description="chapter critique agent",
        enabled=True,
        target_scope="chapter",
        prompt_template="Review this chapter for pacing drift.",
    )
    record = _write_record(initialized_project / ".pizhi" / "cache", "not review markdown")

    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_prompt_request",
        lambda *args, **kwargs: FakeExecution(record=record),
    )

    result = execute_agent_spec(
        initialized_project,
        spec,
        target="project",
        context_markdown="context",
    )

    assert result.status == "failed"
    assert result.failure_reason == "ai review markdown must start with an issue block"
