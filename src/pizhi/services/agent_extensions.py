from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.adapters.base import PromptRequest
from pizhi.domain.agent_extensions import AgentSpec
from pizhi.domain.ai_review import AIReviewIssue
from pizhi.domain.ai_review import ALLOWED_REVIEW_SEVERITIES
from pizhi.domain.ai_review import parse_ai_review_issues
from pizhi.domain.ai_review import parse_structured_issues
from pizhi.services.ai_review_service import NO_AI_REVIEW_ISSUES_MESSAGE
from pizhi.services.provider_execution import execute_prompt_request
from pizhi.services.run_store import RunStore


@dataclass(frozen=True, slots=True)
class ExtensionReportSection:
    agent_id: str
    title: str
    body: str


@dataclass(frozen=True, slots=True)
class AgentExecutionResult:
    agent_id: str
    kind: str
    status: str
    summary: str
    issues: list[AIReviewIssue]
    suggestions: list[str]
    failure_reason: str | None
    run_id: str | None

    @classmethod
    def failed(
        cls,
        spec: AgentSpec,
        failure_reason: str,
        *,
        run_id: str | None = None,
    ) -> "AgentExecutionResult":
        return cls(
            agent_id=spec.agent_id,
            kind=spec.kind,
            status="failed",
            summary="Execution failed",
            issues=[],
            suggestions=[],
            failure_reason=failure_reason,
            run_id=run_id,
        )


def execute_agent_spec(
    project_root: Path,
    spec: AgentSpec,
    *,
    target: str,
    context_markdown: str,
    route_name: str = "review",
) -> AgentExecutionResult:
    prompt_request = PromptRequest(
        command_name=f"{spec.kind}-agent",
        prompt_text=render_agent_prompt(spec, target=target, context_markdown=context_markdown),
        metadata={"agent_id": spec.agent_id, "kind": spec.kind, "target": target},
        referenced_files=[],
    )
    try:
        execution = execute_prompt_request(project_root, prompt_request, target=target, route_name=route_name)
    except Exception as exc:
        return AgentExecutionResult.failed(spec, str(exc))
    return normalize_agent_execution(spec, execution)


def normalize_agent_execution(spec: AgentSpec, execution) -> AgentExecutionResult:
    run_id = getattr(execution, "run_id", None)
    if getattr(execution, "status", None) != "succeeded":
        failure_reason = _read_failure_reason(execution) or getattr(execution, "status", "failed")
        return AgentExecutionResult.failed(spec, failure_reason, run_id=run_id)

    rendered_markdown = _read_normalized_text(execution)
    if rendered_markdown.strip() == NO_AI_REVIEW_ISSUES_MESSAGE.strip():
        return AgentExecutionResult(
            agent_id=spec.agent_id,
            kind=spec.kind,
            status="succeeded",
            summary=_summarize_issues([]),
            issues=[],
            suggestions=[],
            failure_reason=None,
            run_id=run_id,
        )

    try:
        issues = _parse_agent_issues(spec, rendered_markdown)
    except ValueError as exc:
        _mark_failed_run_if_possible(execution, str(exc))
        return AgentExecutionResult.failed(spec, str(exc), run_id=run_id)

    return AgentExecutionResult(
        agent_id=spec.agent_id,
        kind=spec.kind,
        status="succeeded",
        summary=_summarize_issues(issues),
        issues=issues,
        suggestions=[issue.suggestion for issue in issues],
        failure_reason=None,
        run_id=run_id,
    )


def render_agent_prompt(spec: AgentSpec, *, target: str, context_markdown: str) -> str:
    issue_contract_lines = _render_issue_contract(spec.kind)
    return "\n".join(
        [
            "# Agent Extension Request",
            "",
            f"Agent: {spec.agent_id}",
            f"Kind: {spec.kind}",
            f"Target: {target}",
            "",
            "## Description",
            "",
            spec.description,
            "",
            "## Prompt Template",
            "",
            spec.prompt_template.strip(),
            "",
            "## Context",
            "",
            context_markdown.strip(),
            "",
            "Return either the exact no-issues message or Markdown issue blocks in this format:",
            NO_AI_REVIEW_ISSUES_MESSAGE.strip(),
            "",
            *issue_contract_lines,
        ]
    ).rstrip() + "\n"


def render_agent_execution_section(result: AgentExecutionResult) -> ExtensionReportSection:
    if result.status == "failed":
        body = _render_failure_body(
            error_label="execution failure",
            error_text=result.failure_reason or "unknown extension runtime failure",
            fallback_message="unknown extension runtime failure",
            run_id=result.run_id,
        )
        return ExtensionReportSection(
            agent_id=result.agent_id,
            title=f"Review Agent {result.agent_id}",
            body=body,
        )

    if not result.issues:
        body = "- No issues found.\n"
    else:
        body = _render_issue_markdown(result.issues)

    return ExtensionReportSection(
        agent_id=result.agent_id,
        title=f"Review Agent {result.agent_id}",
        body=body,
    )


def render_extension_setup_failure_section(error_text: str) -> ExtensionReportSection:
    return ExtensionReportSection(
        agent_id="extension.setup",
        title="Review Agent extension.setup",
        body=_render_failure_body(
            error_label="extension setup/load failure",
            error_text=error_text,
            fallback_message="unknown extension setup failure",
        ),
    )


def render_extension_runtime_failure_section(agent_id: str, error_text: str) -> ExtensionReportSection:
    return ExtensionReportSection(
        agent_id=agent_id,
        title=f"Review Agent {agent_id}",
        body=_render_failure_body(
            error_label="extension runtime failure",
            error_text=error_text,
            fallback_message="unknown extension runtime failure",
        ),
    )


def _summarize_issues(issues: list[AIReviewIssue]) -> str:
    if not issues:
        return "No issues found"
    count = len(issues)
    return f"{count} issue(s) found"


def _render_issue_markdown(issues: list[AIReviewIssue]) -> str:
    lines: list[str] = []
    for index, issue in enumerate(issues, start=1):
        lines.extend(
            [
                f"### 问题 {index}",
                f"- **类别**：{issue.category}",
                f"- **严重度**：{issue.severity}",
                f"- **描述**：{issue.description}",
                f"- **证据**：{issue.evidence}",
                f"- **建议修法**：{issue.suggestion}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _parse_agent_issues(spec: AgentSpec, rendered_markdown: str) -> list[AIReviewIssue]:
    if spec.kind == "maintenance":
        return parse_structured_issues(rendered_markdown, allowed_severities=ALLOWED_REVIEW_SEVERITIES)
    return parse_ai_review_issues(rendered_markdown)


def _render_issue_contract(kind: str) -> list[str]:
    if kind == "maintenance":
        return [
            "### 问题 1",
            "- **类别**：Archive",
            "- **严重度**：中",
            "- **描述**：...",
            "- **证据**：...",
            "- **建议修法**：...",
        ]
    return [
        "### 问题 1",
        "- **类别**：人物一致性",
        "- **严重度**：高",
        "- **描述**：...",
        "- **证据**：...",
        "- **建议修法**：...",
    ]


def _render_failure_body(
    *,
    error_label: str,
    error_text: str,
    fallback_message: str,
    run_id: str | None = None,
) -> str:
    lines = ["- Status: failed"]
    if run_id:
        lines.append(f"- Run ID: {run_id}")
    lines.append(f"- Error: {error_label}")
    lines.append("")
    lines.extend(_quote_markdown_lines(error_text.strip() or fallback_message))
    return "\n".join(lines).rstrip() + "\n"


def _quote_markdown_lines(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return [">"]
    quoted_lines: list[str] = []
    for line in lines:
        quoted_lines.append("> " + line if line else ">")
    return quoted_lines


def _read_normalized_text(execution) -> str:
    record = getattr(execution, "record", None)
    normalized_path = getattr(record, "normalized_path", None)
    if normalized_path is None:
        return ""
    path = Path(normalized_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _read_failure_reason(execution) -> str:
    record = getattr(execution, "record", None)
    error_path = getattr(record, "error_path", None)
    if error_path is None:
        return ""
    path = Path(error_path)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _mark_failed_run_if_possible(execution, error_text: str) -> None:
    record = getattr(execution, "record", None)
    run_id = getattr(execution, "run_id", None)
    run_dir = getattr(record, "run_dir", None)
    if run_id is None or run_dir is None:
        return
    store = RunStore(Path(run_dir).parent)
    store.mark_failure(run_id, error_text=error_text)
