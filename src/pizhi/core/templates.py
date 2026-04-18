from __future__ import annotations

from pathlib import Path
from typing import Any

from pizhi.services.maintenance import MaintenanceResult


def initial_markdown_files(project_name: str, genre: str) -> dict[Path, str]:
    title_suffix = f" for {project_name}" if project_name else ""
    genre_line = f"Genre: {genre}\n\n" if genre else ""

    return {
        Path("global/synopsis.md"): f"# Synopsis{title_suffix}\n\n{genre_line}",
        Path("global/worldview.md"): "# Worldview\n\n",
        Path("global/timeline.md"): "# Timeline\n\n",
        Path("global/foreshadowing.md"): "# Foreshadowing Tracker\n\n## Active\n\n## Referenced\n\n## Resolved\n\n## Abandoned\n",
        Path("global/characters_index.md"): "# Characters Index\n\n",
        Path("global/outline_global.md"): "# Global Outline\n\n",
        Path("global/rules.md"): "# Rules\n\n",
        Path("chapters/ch000/characters.md"): "# Chapter 000 Characters\n\n",
        Path("chapters/ch000/relationships.md"): "# Chapter 000 Relationships\n\n",
        Path("hooks/pre_chapter.md"): "# Pre Chapter Checklist\n\n",
        Path("hooks/post_chapter.md"): "# Post Chapter Checklist\n\n",
        Path("hooks/consistency_check.md"): "# Consistency Check Template\n\n",
        Path("cache/last_session.md"): "# Last Session\n\n",
        Path("cache/pending_actions.md"): "# Pending Actions\n\n",
    }


def render_checkpoint_summary(
    chapters: list[dict[str, Any]],
    maintenance_results: list[MaintenanceResult | None] | None = None,
) -> str:
    lines = ["# Checkpoint Summary", ""]
    for chapter in chapters:
        lines.append(f"## ch{chapter['number']:03d} | {chapter['title']}")
        lines.append(f"- Summary: {chapter['summary']}")
        lines.append(f"- Character State: {chapter['character_state']}")
        lines.append(f"- Relationship State: {chapter['relationship_state']}")
        introduced = ", ".join(chapter["introduced_ids"]) if chapter["introduced_ids"] else "none"
        resolved = ", ".join(chapter["resolved_ids"]) if chapter["resolved_ids"] else "none"
        lines.append(f"- Foreshadowing Introduced: {introduced}")
        lines.append(f"- Foreshadowing Resolved: {resolved}")
        lines.append("")

    if maintenance_results:
        lines.extend(_render_maintenance_block(maintenance_results))

    return "\n".join(lines).rstrip() + "\n"


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


def _render_maintenance_block(maintenance_results: list[MaintenanceResult | None]) -> list[str]:
    synopsis_summary: str | None = None
    archive_findings: list[str] = []

    for result in maintenance_results:
        if result is None:
            continue
        if result.synopsis_review is not None:
            synopsis_summary = "promoted" if result.synopsis_review.promoted else "rejected"
        archive_findings.extend(finding.detail for finding in result.findings if finding.category == "Archive")

    lines = ["## Maintenance", ""]
    lines.append(
        "- Synopsis review: " + (f"{synopsis_summary}." if synopsis_summary is not None else "not run.")
    )
    if archive_findings:
        lines.append("- Archive findings: " + "; ".join(archive_findings))
    else:
        lines.append("- Archive findings: none.")
    lines.append("")
    return lines
