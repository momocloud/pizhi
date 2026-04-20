from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.adapters.base import PromptRequest
from pizhi.domain.ai_review import AIReviewIssue
from pizhi.domain.ai_review import parse_ai_review_issues
from pizhi.services.ai_review_context import AIReviewContext
from pizhi.services.provider_execution import execute_prompt_request
from pizhi.services.run_store import RunRecord
from pizhi.services.run_store import RunStore


NO_AI_REVIEW_ISSUES_MESSAGE = "- 未发现 B 类 AI 语义问题。\n"


@dataclass(frozen=True, slots=True)
class AIReviewResult:
    status: str
    run_id: str | None
    issues: list[AIReviewIssue]
    rendered_markdown: str
    error_message: str | None
    record: RunRecord | None


def build_ai_review_prompt(context: AIReviewContext) -> str:
    lines = [
        "# AI Review Request",
        "",
        f"Scope: {context.scope}",
        f"Target: {context.target}",
        "",
        "## Prompt Context",
        "",
        context.prompt_context.strip(),
        "",
        "## Referenced Files",
        "",
        *(_render_referenced_files(context.referenced_files)),
        "",
        "## Metadata",
        "",
        *(_render_metadata(context.metadata)),
        "",
        "Return either the exact no-issues message or Markdown issue blocks in this format:",
        NO_AI_REVIEW_ISSUES_MESSAGE.strip(),
        "",
        "### 问题 1",
        "- **类别**：人物一致性",
        "- **严重度**：高",
        "- **描述**：...",
        "- **证据**：...",
        "- **建议修法**：...",
    ]
    return "\n".join(lines).rstrip() + "\n"


def run_ai_review(project_root: Path, context: AIReviewContext) -> AIReviewResult:
    prompt_request = PromptRequest(
        command_name="review",
        prompt_text=build_ai_review_prompt(context),
        metadata=context.metadata,
        referenced_files=context.referenced_files,
    )

    try:
        execution = execute_prompt_request(
            project_root,
            prompt_request,
            target=context.target,
            route_name="review",
        )
    except Exception as exc:
        return AIReviewResult(
            status="failed",
            run_id=None,
            issues=[],
            rendered_markdown="",
            error_message=str(exc),
            record=None,
        )

    rendered_markdown = _read_text(execution.record.normalized_path)
    if execution.status != "succeeded":
        return AIReviewResult(
            status="failed",
            run_id=execution.run_id,
            issues=[],
            rendered_markdown=rendered_markdown,
            error_message=_read_error_text(execution.record) or execution.status,
            record=execution.record,
        )

    if rendered_markdown.strip() == NO_AI_REVIEW_ISSUES_MESSAGE.strip():
        return AIReviewResult(
            status="succeeded",
            run_id=execution.run_id,
            issues=[],
            rendered_markdown=NO_AI_REVIEW_ISSUES_MESSAGE,
            error_message=None,
            record=execution.record,
        )

    try:
        issues = parse_ai_review_issues(rendered_markdown)
    except ValueError as exc:
        store = RunStore(execution.record.run_dir.parent)
        record = store.mark_failure(execution.run_id, error_text=str(exc))
        return AIReviewResult(
            status="failed",
            run_id=execution.run_id,
            issues=[],
            rendered_markdown=rendered_markdown,
            error_message=str(exc),
            record=record,
        )

    return AIReviewResult(
        status="succeeded",
        run_id=execution.run_id,
        issues=issues,
        rendered_markdown=format_ai_review_issues(issues),
        error_message=None,
        record=execution.record,
    )


def format_ai_review_issues(issues: list[AIReviewIssue]) -> str:
    if not issues:
        return NO_AI_REVIEW_ISSUES_MESSAGE

    blocks = [_format_ai_review_issue(issue, index=index) for index, issue in enumerate(issues, start=1)]
    return "\n\n".join(blocks).rstrip() + "\n"


def _render_referenced_files(referenced_files: list[str]) -> list[str]:
    if not referenced_files:
        return ["- (none)"]
    return [f"- {path}" for path in sorted(referenced_files)]


def _render_metadata(metadata: dict[str, object]) -> list[str]:
    if not metadata:
        return ["- (none)"]
    return [f"- {key}: {metadata[key]}" for key in sorted(metadata)]


def _format_ai_review_issue(issue: AIReviewIssue, *, index: int) -> str:
    return "\n".join(
        [
            f"### 问题 {index}",
            f"- **类别**：{issue.category}",
            f"- **严重度**：{issue.severity}",
            f"- **描述**：{issue.description}",
            f"- **证据**：{issue.evidence}",
            f"- **建议修法**：{issue.suggestion}",
        ]
    )


def _read_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _read_error_text(record: RunRecord) -> str:
    if record.error_path.exists():
        return record.error_path.read_text(encoding="utf-8").strip()
    return ""
