from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.consistency.structural import format_structural_report
from pizhi.services.consistency.structural import run_structural_review
from pizhi.services.ai_review_context import build_chapter_ai_review_context
from pizhi.services.ai_review_context import build_full_ai_review_context
from pizhi.services.ai_review_service import run_ai_review
from pizhi.services.maintenance import format_maintenance_summary
from pizhi.services.maintenance import run_full_maintenance
from pizhi.services.review_documents import load_chapter_review_notes
from pizhi.services.review_documents import write_full_review_document
from pizhi.services.review_documents import write_chapter_review_notes


def run_review(args: argparse.Namespace) -> int:
    project_root = Path.cwd()
    report = run_structural_review(project_root, chapter_number=args.chapter, full=args.full)
    maintenance_result = run_full_maintenance(project_root) if args.full else None
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
    print(f"Run ID: {result.run_id or 'n/a'}")

    notes_path = project_paths(project_root).chapter_dir(chapter_number) / "notes.md"
    notes = load_chapter_review_notes(notes_path)
    write_chapter_review_notes(
        notes_path,
        author_notes=notes.author_notes,
        structural_markdown=_render_structural_body(report.chapter_issues.get(chapter_number, [])),
        ai_review_markdown=_render_ai_review_markdown(result),
    )
    return 0 if result.status == "succeeded" else 1


def _run_full_execute_review(project_root: Path, report, maintenance_result) -> int:
    report_path = _write_full_review_base_document(project_root, report, maintenance_result)
    context = build_full_ai_review_context(project_root, report, maintenance_result)
    result = run_ai_review(project_root, context)
    print(f"Run ID: {result.run_id or 'n/a'}")

    _write_full_review_document(report_path, report, maintenance_result, _render_ai_review_markdown(result))
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


def _write_full_review_document(report_path: Path, report, maintenance_result, ai_review_markdown: str) -> None:
    write_full_review_document(
        report_path,
        summary_markdown=_render_full_review_summary(report, maintenance_result),
        structural_markdown=format_structural_report(report),
        maintenance_markdown=_render_maintenance_body(maintenance_result),
        ai_review_markdown=ai_review_markdown,
    )


def _render_pending_ai_review_markdown() -> str:
    return "- 未执行 AI 审查。\n"


    
