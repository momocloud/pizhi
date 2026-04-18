from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


def run_after_write(project_root: Path) -> MaintenanceResult:
    return _run_maintenance(project_root)


def run_full_maintenance(project_root: Path) -> MaintenanceResult:
    return _run_maintenance(project_root)


def _run_maintenance(project_root: Path) -> MaintenanceResult:
    synopsis_review = None
    candidate_path = project_root / ".pizhi" / "global" / "synopsis_candidate.md"
    if candidate_path.exists():
        synopsis_review = review_synopsis_candidate(project_root)

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
