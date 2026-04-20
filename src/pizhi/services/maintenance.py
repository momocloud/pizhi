from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pizhi.core.paths import project_paths
from pizhi.services.agent_registry import load_agent_registry
from pizhi.services.archive_service import ArchiveResult
from pizhi.services.archive_service import rotate_archives
from pizhi.services.synopsis_review import SynopsisReviewResult
from pizhi.services.synopsis_review import review_synopsis_candidate

if TYPE_CHECKING:
    from pizhi.services.agent_extensions import AgentExecutionResult


@dataclass(frozen=True, slots=True)
class MaintenanceFinding:
    category: str
    detail: str


@dataclass(frozen=True, slots=True)
class MaintenanceResult:
    synopsis_review: SynopsisReviewResult | None
    archive_result: ArchiveResult | None
    findings: list[MaintenanceFinding]


def mark_synopsis_review_pending(project_root: Path) -> None:
    marker_path = _synopsis_review_pending_path(project_root)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text("pending\n", encoding="utf-8", newline="\n")


def clear_synopsis_review_pending(project_root: Path) -> None:
    marker_path = _synopsis_review_pending_path(project_root)
    if marker_path.exists():
        marker_path.unlink()


def run_after_write(project_root: Path, *, include_extensions: bool = True) -> MaintenanceResult:
    return _run_maintenance(project_root, include_extensions=include_extensions)


def run_full_maintenance(project_root: Path, *, include_extensions: bool = True) -> MaintenanceResult:
    return _run_maintenance(project_root, include_extensions=include_extensions)


def _run_maintenance(project_root: Path, *, include_extensions: bool) -> MaintenanceResult:
    core_result = _run_core_maintenance(project_root)
    if not include_extensions:
        return core_result

    extension_findings = _run_maintenance_extension_findings(
        project_root,
        core_result.synopsis_review,
        core_result.archive_result,
    )
    if not extension_findings:
        return core_result
    return MaintenanceResult(
        synopsis_review=core_result.synopsis_review,
        archive_result=core_result.archive_result,
        findings=core_result.findings + extension_findings,
    )


def _run_core_maintenance(project_root: Path) -> MaintenanceResult:
    synopsis_review = None
    candidate_path = project_paths(project_root).synopsis_candidate_file
    marker_path = _synopsis_review_pending_path(project_root)
    if marker_path.exists() and candidate_path.exists():
        synopsis_review = review_synopsis_candidate(project_root)
    clear_synopsis_review_pending(project_root)

    archive_result = rotate_archives(project_root)
    findings = _build_findings(synopsis_review, archive_result, [])
    return MaintenanceResult(
        synopsis_review=synopsis_review,
        archive_result=archive_result,
        findings=findings,
    )


def _build_findings(
    synopsis_review: SynopsisReviewResult | None,
    archive_result: ArchiveResult | None,
    extension_findings: list[MaintenanceFinding],
) -> list[MaintenanceFinding]:
    findings: list[MaintenanceFinding] = []

    if synopsis_review is not None:
        findings.append(
            MaintenanceFinding(
                category="Synopsis review",
                detail=(
                    "promoted synopsis candidate into synopsis.md"
                    if synopsis_review.promoted
                    else "rejected synopsis candidate; see cache/synopsis_review.md"
                ),
            )
        )

    if archive_result is not None:
        for finding in archive_result.findings:
            findings.append(
                MaintenanceFinding(
                    category="Archive",
                    detail=finding.description,
                )
            )

    findings.extend(extension_findings)
    return findings


def _run_maintenance_extension_findings(
    project_root: Path,
    synopsis_review: SynopsisReviewResult | None,
    archive_result: ArchiveResult | None,
) -> list[MaintenanceFinding]:
    from pizhi.services.agent_extensions import execute_agent_spec

    try:
        registry = load_agent_registry(project_root)
        maintenance_agents = registry.iter_enabled(kind="maintenance", target_scope="project")
    except Exception as exc:
        return [_build_maintenance_extension_failure_finding("extension.setup", str(exc))]

    context_markdown = build_maintenance_context(synopsis_review, archive_result)
    findings: list[MaintenanceFinding] = []
    for spec in maintenance_agents:
        try:
            result = execute_agent_spec(
                project_root,
                spec,
                target="project",
                context_markdown=context_markdown,
                route_name="review",
            )
        except Exception as exc:
            findings.append(_build_maintenance_extension_failure_finding(spec.agent_id, str(exc)))
            continue
        finding = _build_maintenance_extension_result_finding(result)
        if finding is not None:
            findings.append(finding)
    return findings


def build_maintenance_context(
    synopsis_review: SynopsisReviewResult | None,
    archive_result: ArchiveResult | None,
) -> str:
    lines = ["# Maintenance Context", ""]
    if synopsis_review is None:
        lines.extend(["## Synopsis review", "", "- Not run.", ""])
    else:
        synopsis_status = "promoted" if synopsis_review.promoted else "rejected"
        lines.extend(["## Synopsis review", "", f"- Status: {synopsis_status}.", ""])

    lines.extend(["## Archive findings", ""])
    archive_findings = archive_result.findings if archive_result is not None else []
    if archive_findings:
        for finding in archive_findings:
            lines.append(f"- {finding.description}")
    else:
        lines.append("- None.")
    return "\n".join(lines).rstrip() + "\n"


def _build_maintenance_extension_result_finding(result: AgentExecutionResult) -> MaintenanceFinding | None:
    if result.status == "succeeded":
        if not result.issues and result.summary == "No issues found":
            return None
        detail = _format_maintenance_extension_success(result)
    else:
        detail = f"{result.agent_id}: failed - {result.failure_reason or 'unknown failure'}"
    return MaintenanceFinding(category="Maintenance agent", detail=detail)


def _build_maintenance_extension_failure_finding(agent_id: str, error_text: str) -> MaintenanceFinding:
    detail = f"{agent_id}: failed - {error_text.strip() or 'unknown extension runtime failure'}"
    return MaintenanceFinding(category="Maintenance agent", detail=detail)


def _format_maintenance_extension_success(result: AgentExecutionResult) -> str:
    if not result.issues:
        return f"{result.agent_id}: {result.summary}"

    issue_summaries = [
        f"[{issue.severity}] {issue.category}: {issue.description} 证据：{issue.evidence} 建议：{issue.suggestion}"
        for issue in result.issues
    ]
    return f"{result.agent_id}: {'; '.join(issue_summaries)}"


def format_maintenance_summary(maintenance_result: MaintenanceResult | None) -> str:
    if maintenance_result is None:
        return "## Maintenance\n\n- No maintenance run.\n"

    lines = ["## Maintenance", ""]
    if maintenance_result.synopsis_review is None:
        lines.append("- Synopsis review: not run.")
    else:
        status = "promoted" if maintenance_result.synopsis_review.promoted else "rejected"
        lines.append(f"- Synopsis review: {status}.")

    archive_findings = maintenance_result.archive_result.findings if maintenance_result.archive_result is not None else []
    if archive_findings:
        lines.append(f"- Archive findings: {len(archive_findings)}.")
    else:
        lines.append("- Archive findings: none.")

    if maintenance_result.findings:
        lines.append("")
        for finding in maintenance_result.findings:
            lines.append(f"- {finding.category}: {finding.detail}")
    return "\n".join(lines).rstrip() + "\n"


def format_checkpoint_maintenance(chapter_results: list[tuple[int, MaintenanceResult | None]]) -> str:
    lines = ["## Maintenance", ""]

    for chapter_number, result in chapter_results:
        if result is None:
            lines.append(f"- ch{chapter_number:03d}: no maintenance run.")
            continue

        if result.synopsis_review is None:
            synopsis_state = "no synopsis review"
        else:
            synopsis_state = "promoted" if result.synopsis_review.promoted else "rejected"
            synopsis_state = f"Synopsis review {synopsis_state}"
        lines.append(f"- ch{chapter_number:03d}: {synopsis_state}")

        archive_details = [finding.detail for finding in result.findings if finding.category == "Archive"]
        if archive_details:
            lines.append(f"  archive: {'; '.join(archive_details)}")

        maintenance_agent_details = [finding.detail for finding in result.findings if finding.category == "Maintenance agent"]
        if maintenance_agent_details:
            lines.append(f"  Maintenance agent: {'; '.join(maintenance_agent_details)}")

    return "\n".join(lines).rstrip() + "\n"


def _synopsis_review_pending_path(project_root: Path) -> Path:
    return project_paths(project_root).cache_dir / "synopsis_review.pending"
