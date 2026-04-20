from __future__ import annotations

import argparse
from pathlib import Path
import sys

from pizhi.core.paths import project_paths
from pizhi.services.consistency.structural import run_structural_review
from pizhi.services.consistency.structural import REQUIRED_ARTIFACT_NAMES
from pizhi.services.ai_review_context import build_chapter_ai_review_context
from pizhi.services.ai_review_context import build_full_ai_review_context
from pizhi.services.ai_review_service import run_ai_review
from pizhi.services.agent_extensions import execute_agent_spec
from pizhi.services.agent_extensions import render_extension_runtime_failure_section
from pizhi.services.agent_extensions import render_extension_setup_failure_section
from pizhi.services.agent_extensions import render_agent_execution_section
from pizhi.services.agent_registry import load_agent_registry
from pizhi.services.maintenance import format_maintenance_summary
from pizhi.services.maintenance import run_full_maintenance
from pizhi.services.review_documents import load_chapter_review_notes
from pizhi.services.review_documents import write_full_review_document
from pizhi.services.review_documents import write_chapter_review_notes
from pizhi.services.project_snapshot import load_project_snapshot


def run_review(args: argparse.Namespace) -> int:
    execute = getattr(args, "execute", False)
    if execute and not _review_execute_scope_is_valid(args):
        print("error: review --execute requires --chapter N or --full", file=sys.stderr)
        return 2

    project_root = Path.cwd()
    if execute and not args.full and args.chapter is not None:
        snapshot = load_project_snapshot(project_root)
        target_error = _review_chapter_execute_target_error(project_root, snapshot, args.chapter)
        if target_error is not None:
            print(f"error: {target_error}", file=sys.stderr)
            return 2

    report = run_structural_review(project_root, chapter_number=args.chapter, full=args.full)
    maintenance_result = None
    if args.full:
        maintenance_result = run_full_maintenance(project_root, include_extensions=execute)
    print(f"Chapters reviewed: {report.chapters_reviewed}")
    print(f"Chapters with issues: {report.chapters_with_issues}")
    print(f"Chapter issues: {report.total_chapter_issues}")
    print(f"Global issues: {len(report.global_issues)}")
    if maintenance_result is not None:
        print(f"Maintenance findings: {len(maintenance_result.findings)}")

    if not getattr(args, "execute", False):
        if args.full:
            report_path = _write_full_review_base_document(project_root, report, maintenance_result)
            print(f"Full report: {report_path}")
        return 0

    if args.full:
        return _run_full_execute_review(project_root, report, maintenance_result)

    if args.chapter is None:
        raise ValueError("chapter number is required when executing a chapter review")
    return _run_chapter_execute_review(project_root, args.chapter, report)


def _run_chapter_execute_review(project_root: Path, chapter_number: int, report) -> int:
    context = build_chapter_ai_review_context(project_root, chapter_number, report.chapter_issues.get(chapter_number, []))
    result = run_ai_review(project_root, context)
    extension_sections = _run_review_extension_sections(project_root, target_scope="chapter", target_name=context.target, context_markdown=context.prompt_context)
    print(f"Run ID: {result.run_id or 'n/a'}")

    notes_path = project_paths(project_root).chapter_dir(chapter_number) / "notes.md"
    notes = load_chapter_review_notes(notes_path)
    write_chapter_review_notes(
        notes_path,
        author_notes=notes.author_notes,
        structural_markdown=_render_structural_body(report.chapter_issues.get(chapter_number, [])),
        ai_review_markdown=_render_ai_review_markdown(result),
        extension_sections=extension_sections,
    )
    return 0 if result.status == "succeeded" else 1


def _run_full_execute_review(project_root: Path, report, maintenance_result) -> int:
    report_path = _write_full_review_base_document(project_root, report, maintenance_result)
    context = build_full_ai_review_context(project_root, report, maintenance_result)
    result = run_ai_review(project_root, context)
    extension_sections = _run_review_extension_sections(project_root, target_scope="project", target_name=context.target, context_markdown=context.prompt_context)
    print(f"Run ID: {result.run_id or 'n/a'}")

    _write_full_review_document(
        report_path,
        report,
        maintenance_result,
        _render_ai_review_markdown(result),
        extension_sections=extension_sections,
    )
    print(f"Full report: {report_path}")
    return 0 if result.status == "succeeded" else 1


def _render_full_review_summary(report, maintenance_result) -> str:
    lines = [
        f"- Chapters reviewed: {report.chapters_reviewed}",
        f"- Chapters with issues: {report.chapters_with_issues}",
        f"- Chapter issues: {report.total_chapter_issues}",
        f"- Global issues: {len(report.global_issues)}",
    ]
    if maintenance_result is not None:
        lines.append(f"- Maintenance findings: {len(maintenance_result.findings)}")
    return "\n".join(lines).rstrip() + "\n"


def _review_execute_scope_is_valid(args: argparse.Namespace) -> bool:
    return bool(args.full or args.chapter is not None)


def _review_chapter_execute_target_error(project_root: Path, snapshot, chapter_number: int) -> str | None:
    if chapter_number not in snapshot.chapters:
        return f"chapter {chapter_number} does not exist in the chapter index"

    chapter_dir = project_paths(project_root).chapter_dir(chapter_number)
    if not chapter_dir.exists():
        return f"chapter {chapter_number} is missing its chapter directory"

    missing_artifacts = [name for name in REQUIRED_ARTIFACT_NAMES if not _path_has_content(chapter_dir / name)]
    if missing_artifacts:
        missing_list = ", ".join(missing_artifacts)
        return f"chapter {chapter_number} is missing required files: {missing_list}"

    return None


def _render_structural_body(issues) -> str:
    if not issues:
        return "- 未发现结构化问题。\n"

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


def _path_has_content(path: Path) -> bool:
    return path.exists() and bool(path.read_text(encoding="utf-8").strip())


def _render_ai_review_markdown(result) -> str:
    if result.status == "succeeded":
        return result.rendered_markdown
    lines = ["AI 审查执行失败。"]
    if result.run_id:
        lines.append(f"Run ID: {result.run_id}")
    if result.error_message:
        lines.append("")
        lines.append(result.error_message)
    return "\n".join(lines).rstrip() + "\n"


def _render_maintenance_body(maintenance_result) -> str:
    summary = format_maintenance_summary(maintenance_result).rstrip()
    prefix = "## Maintenance\n\n"
    if summary.startswith(prefix):
        return summary.removeprefix(prefix)
    return summary


def _write_full_review_base_document(project_root: Path, report, maintenance_result) -> Path:
    report_path = project_paths(project_root).cache_dir / "review_full.md"
    _write_full_review_document(report_path, report, maintenance_result, _render_pending_ai_review_markdown())
    return report_path


def _write_full_review_document(
    report_path: Path,
    report,
    maintenance_result,
    ai_review_markdown: str,
    *,
    extension_sections=None,
) -> None:
    write_full_review_document(
        report_path,
        summary_markdown=_render_full_review_summary(report, maintenance_result),
        structural_markdown=_render_full_structural_body(report),
        maintenance_markdown=_render_maintenance_body(maintenance_result),
        ai_review_markdown=ai_review_markdown,
        extension_sections=extension_sections,
    )


def _render_pending_ai_review_markdown() -> str:
    return "- 未执行 AI 审查。\n"


def _render_full_structural_body(report) -> str:
    lines: list[str] = []
    lines.extend(_render_full_structural_group("Global issues", report.global_issues))

    for chapter_number in sorted(report.chapter_issues):
        issues = report.chapter_issues[chapter_number]
        lines.append("")
        lines.extend(_render_full_structural_group(f"ch{chapter_number:03d}", issues))

    return "\n".join(lines).rstrip() + "\n"


def _render_full_structural_group(name: str, issues) -> list[str]:
    lines = [f"### {name}", ""]
    if not issues:
        lines.append("- None.")
        return lines

    for index, issue in enumerate(issues, start=1):
        lines.extend(
            [
                f"#### Issue {index}",
                f"- Category: {issue.category}",
                f"- Severity: {issue.severity}",
                f"- Description: {issue.description}",
                f"- Evidence: {issue.evidence}",
                f"- Suggestion: {issue.suggestion}",
                "",
            ]
        )
    return lines


def _run_review_extension_sections(
    project_root: Path,
    *,
    target_scope: str,
    target_name: str,
    context_markdown: str,
):
    try:
        registry = load_agent_registry(project_root)
        review_agents = registry.iter_enabled(kind="review", target_scope=target_scope)
    except Exception as exc:
        return [render_extension_setup_failure_section(str(exc))]

    sections = []
    for spec in review_agents:
        try:
            sections.append(
                render_agent_execution_section(
                    execute_agent_spec(
                        project_root,
                        spec,
                        target=target_name,
                        context_markdown=context_markdown,
                        route_name="review",
                    )
                )
            )
        except Exception as exc:
            sections.append(render_extension_runtime_failure_section(spec.agent_id, str(exc)))
    return sections


    
