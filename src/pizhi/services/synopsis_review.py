from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pizhi.core.paths import project_paths
from pizhi.services.project_snapshot import load_project_snapshot


MARKER_SECTION_RE = re.compile(r"^## coverage_markers\s*$", re.MULTILINE)
MARKER_NAME_RE = re.compile(r"^\s*-?\s*(foreshadowing_ids|major_turning_points):(?P<rest>.*)$")
MARKER_ID_RE = re.compile(r"^\s*-\s+(?P<id>\S+)\s*$")


@dataclass(frozen=True, slots=True)
class SynopsisCandidateMarkers:
    foreshadowing_ids: tuple[str, ...]
    major_turning_points: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SynopsisReviewResult:
    promoted: bool
    review_text: str
    synopsis_path: Path
    candidate_path: Path
    review_path: Path
    missing_foreshadowing_ids: tuple[str, ...]
    missing_major_turning_point_ids: tuple[str, ...]
    unexpected_foreshadowing_ids: tuple[str, ...]
    unexpected_major_turning_point_ids: tuple[str, ...]


def parse_synopsis_candidate(raw: str) -> tuple[str, SynopsisCandidateMarkers]:
    marker_match = MARKER_SECTION_RE.search(raw)
    if marker_match is None:
        raise ValueError("missing coverage_markers section")

    body = raw[: marker_match.start()].rstrip()
    if not body.strip():
        raise ValueError("synopsis candidate body cannot be empty")

    markers_text = raw[marker_match.end() :].strip()
    if not markers_text:
        raise ValueError("coverage_markers section cannot be empty")

    markers = _parse_markers(markers_text)
    return body, markers


def review_synopsis_candidate(project_root: Path) -> SynopsisReviewResult:
    paths = project_paths(project_root)
    snapshot = load_project_snapshot(project_root)
    candidate_path = paths.synopsis_candidate_file
    review_path = paths.cache_dir / "synopsis_review.md"
    synopsis_path = paths.synopsis_file

    raw_candidate = candidate_path.read_text(encoding="utf-8")

    try:
        body, markers = parse_synopsis_candidate(raw_candidate)
    except ValueError as exc:
        review_text = _render_review(False, (), (), error=str(exc))
        _write_text(review_path, review_text)
        return SynopsisReviewResult(
            promoted=False,
            review_text=review_text,
            synopsis_path=synopsis_path,
            candidate_path=candidate_path,
            review_path=review_path,
            missing_foreshadowing_ids=(),
            missing_major_turning_point_ids=(),
            unexpected_foreshadowing_ids=(),
            unexpected_major_turning_point_ids=(),
        )

    required_foreshadowing_ids = {entry.entry_id for entry in snapshot.active_or_referenced_foreshadowing}
    required_major_turning_point_ids = {entry.event_id for entry in snapshot.major_turning_points}

    marker_foreshadowing_ids = set(markers.foreshadowing_ids)
    marker_major_turning_point_ids = set(markers.major_turning_points)

    missing_foreshadowing_ids = tuple(sorted(required_foreshadowing_ids - marker_foreshadowing_ids))
    missing_major_turning_point_ids = tuple(sorted(required_major_turning_point_ids - marker_major_turning_point_ids))
    unexpected_foreshadowing_ids = tuple(sorted(marker_foreshadowing_ids - required_foreshadowing_ids))
    unexpected_major_turning_point_ids = tuple(sorted(marker_major_turning_point_ids - required_major_turning_point_ids))
    promoted = (
        not missing_foreshadowing_ids
        and not missing_major_turning_point_ids
        and not unexpected_foreshadowing_ids
        and not unexpected_major_turning_point_ids
    )

    review_text = _render_review(
        promoted,
        missing_foreshadowing_ids,
        missing_major_turning_point_ids,
        unexpected_foreshadowing_ids,
        unexpected_major_turning_point_ids,
        error=None,
    )
    _write_text(review_path, review_text)

    if promoted:
        _write_text(synopsis_path, body + "\n")
        if candidate_path.exists():
            candidate_path.unlink()

    return SynopsisReviewResult(
        promoted=promoted,
        review_text=review_text,
        synopsis_path=synopsis_path,
        candidate_path=candidate_path,
        review_path=review_path,
        missing_foreshadowing_ids=missing_foreshadowing_ids,
        missing_major_turning_point_ids=missing_major_turning_point_ids,
        unexpected_foreshadowing_ids=unexpected_foreshadowing_ids,
        unexpected_major_turning_point_ids=unexpected_major_turning_point_ids,
    )


def _parse_markers(markers_text: str) -> SynopsisCandidateMarkers:
    sections: dict[str, list[str]] = {
        "foreshadowing_ids": [],
        "major_turning_points": [],
    }
    current_section: str | None = None
    seen_sections: set[str] = set()

    for line in markers_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        name_match = MARKER_NAME_RE.fullmatch(stripped)
        if name_match is not None:
            current_section = name_match.group(1)
            seen_sections.add(current_section)
            inline_ids = [item.strip() for item in name_match.group("rest").split(",") if item.strip()]
            sections[current_section].extend(inline_ids)
            continue

        item_match = MARKER_ID_RE.fullmatch(stripped)
        if item_match is None or current_section is None:
            raise ValueError("malformed coverage_markers section")
        sections[current_section].append(item_match.group("id"))

    missing_sections = [name for name in ("foreshadowing_ids", "major_turning_points") if name not in seen_sections]
    if missing_sections:
        raise ValueError(f"missing marker sections: {', '.join(missing_sections)}")

    return SynopsisCandidateMarkers(
        foreshadowing_ids=tuple(sections["foreshadowing_ids"]),
        major_turning_points=tuple(sections["major_turning_points"]),
    )


def _render_review(
    promoted: bool,
    missing_foreshadowing_ids: tuple[str, ...],
    missing_major_turning_point_ids: tuple[str, ...],
    unexpected_foreshadowing_ids: tuple[str, ...],
    unexpected_major_turning_point_ids: tuple[str, ...],
    *,
    error: str | None,
) -> str:
    lines = ["# Synopsis Review", ""]
    lines.append(f"status: {'promoted' if promoted else 'rejected'}")
    if error is not None:
        lines.extend(["", f"error: {error}"])
        return "\n".join(lines).rstrip() + "\n"

    lines.extend(
        [
            "",
            "missing foreshadowing ids: " + (", ".join(missing_foreshadowing_ids) if missing_foreshadowing_ids else "none"),
            "missing major turning points: "
            + (", ".join(missing_major_turning_point_ids) if missing_major_turning_point_ids else "none"),
            "unexpected foreshadowing ids: "
            + (", ".join(unexpected_foreshadowing_ids) if unexpected_foreshadowing_ids else "none"),
            "unexpected major turning points: "
            + (", ".join(unexpected_major_turning_point_ids) if unexpected_major_turning_point_ids else "none"),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
