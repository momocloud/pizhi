from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.archive_service import ArchiveResult
from pizhi.services.archive_service import rotate_archives
from pizhi.services.synopsis_review import SynopsisReviewResult
from pizhi.services.synopsis_review import review_synopsis_candidate


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


def run_after_write(project_root: Path) -> MaintenanceResult:
    return _run_maintenance(project_root)


def run_full_maintenance(project_root: Path) -> MaintenanceResult:
    return _run_maintenance(project_root)


def _run_maintenance(project_root: Path) -> MaintenanceResult:
    synopsis_review = None
    candidate_path = project_paths(project_root).synopsis_candidate_file
    marker_path = _synopsis_review_pending_path(project_root)
    if marker_path.exists() and candidate_path.exists():
        synopsis_review = review_synopsis_candidate(project_root)
    clear_synopsis_review_pending(project_root)

    archive_result = rotate_archives(project_root)
    findings = _build_findings(synopsis_review, archive_result)
    return MaintenanceResult(
        synopsis_review=synopsis_review,
        archive_result=archive_result,
        findings=findings,
    )


def _build_findings(
    synopsis_review: SynopsisReviewResult | None,
    archive_result: ArchiveResult | None,
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

    return findings


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

    return "\n".join(lines).rstrip() + "\n"


def _synopsis_review_pending_path(project_root: Path) -> Path:
    return project_paths(project_root).cache_dir / "synopsis_review.pending"
