from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.domain.project_state import ProjectSnapshot
from pizhi.services.consistency.structural import StructuralIssue
from pizhi.services.consistency.structural import StructuralReport
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.maintenance import format_maintenance_summary
from pizhi.services.project_snapshot import load_project_snapshot


@dataclass(frozen=True, slots=True)
class AIReviewContext:
    scope: str
    target: str
    prompt_context: str
    referenced_files: list[str]
    metadata: dict[str, object]


def build_chapter_ai_review_context(
    project_root: Path,
    chapter_number: int,
    structural_issues: list[StructuralIssue],
) -> AIReviewContext:
    paths = project_paths(project_root)
    snapshot = load_project_snapshot(project_root)
    chapter_dir = paths.chapter_dir(chapter_number)
    previous_dir = paths.chapter_dir(chapter_number - 1) if chapter_number > 1 else None
    current_text = _read_text(chapter_dir / "text.md")
    previous_text = _read_text(previous_dir / "text.md") if previous_dir is not None else ""
    worldview_text = _read_text(paths.worldview_file)
    chapter_state = snapshot.chapters.get(chapter_number)

    prompt_context = "\n".join(
        [
            "# Chapter AI Review Context",
            "",
            _render_chapter_snapshot(snapshot, chapter_number, chapter_state),
            "## 当前章节正文",
            "",
            current_text or "（缺失）",
            "",
            "## 上一章正文",
            "",
            previous_text or "（无上一章）",
            "",
            "## 世界观",
            "",
            worldview_text or "（无世界观内容）",
            "",
            "## A 类结构问题",
            "",
            _render_a_class_issues(structural_issues),
        ]
    ).rstrip() + "\n"

    referenced_files = [
        _relative_path(project_root, chapter_dir / "text.md"),
        _relative_path(project_root, paths.worldview_file),
    ]
    if previous_dir is not None:
        referenced_files.append(_relative_path(project_root, previous_dir / "text.md"))
    if chapter_number > 1:
        referenced_files.extend(
            [
                _relative_path(project_root, previous_dir / "characters.md"),
                _relative_path(project_root, previous_dir / "relationships.md"),
            ]
        )

    metadata: dict[str, object] = {
        "scope": "chapter",
        "chapter": chapter_number,
        "latest_chapter": snapshot.latest_chapter,
        "issue_count": len(structural_issues),
    }
    if chapter_state is not None:
        metadata["chapter_title"] = chapter_state.title
        metadata["chapter_status"] = chapter_state.status

    return AIReviewContext(
        scope="chapter",
        target=f"ch{chapter_number:03d}",
        prompt_context=prompt_context,
        referenced_files=referenced_files,
        metadata=metadata,
    )


def build_full_ai_review_context(
    project_root: Path,
    report: StructuralReport,
    maintenance_result: MaintenanceResult,
) -> AIReviewContext:
    paths = project_paths(project_root)
    snapshot = load_project_snapshot(project_root)
    prompt_context = "\n".join(
        [
            "# Full AI Review Context",
            "",
            _render_project_snapshot(snapshot),
            "## 活跃伏笔",
            "",
            _render_active_foreshadowing(snapshot),
            "",
            "## 重大转折",
            "",
            _render_major_turning_points(snapshot),
            "",
            "## A 类全书问题",
            "",
            _render_a_class_issues(report.global_issues),
            "",
            format_maintenance_summary(maintenance_result).rstrip(),
        ]
    ).rstrip() + "\n"

    referenced_files = [
        _relative_path(project_root, paths.synopsis_file),
        _relative_path(project_root, paths.worldview_file),
        _relative_path(project_root, paths.timeline_file),
        _relative_path(project_root, paths.foreshadowing_file),
    ]
    referenced_files.extend(
        _relative_path(project_root, chapter.chapter_dir / "text.md")
        for chapter in snapshot.recent_chapters[:3]
    )

    metadata: dict[str, object] = {
        "scope": "full",
        "chapters_reviewed": report.chapters_reviewed,
        "chapter_issues": report.total_chapter_issues,
        "global_issues": len(report.global_issues),
        "active_foreshadowing": len([entry for entry in snapshot.foreshadowing_entries if entry.section == "Active"]),
        "major_turning_points": len(snapshot.major_turning_points),
        "maintenance_findings": len(maintenance_result.findings),
    }

    return AIReviewContext(
        scope="full",
        target="project",
        prompt_context=prompt_context,
        referenced_files=referenced_files,
        metadata=metadata,
    )


def _render_chapter_snapshot(snapshot: ProjectSnapshot, chapter_number: int, chapter_state) -> str:
    lines = ["## 章节快照", ""]
    lines.append(f"- 目标章节: ch{chapter_number:03d}")
    lines.append(f"- 最新章节: {f'ch{snapshot.latest_chapter:03d}' if snapshot.latest_chapter is not None else '无'}")
    if chapter_state is not None:
        lines.append(f"- 章节标题: {chapter_state.title}")
        lines.append(f"- 章节状态: {chapter_state.status}")
    lines.append("")
    return "\n".join(lines).rstrip()


def _render_project_snapshot(snapshot: ProjectSnapshot) -> str:
    lines = ["## 项目快照", ""]
    lines.append(f"- 项目名称: {snapshot.project_name}")
    lines.append(f"- 已记录章节: {len(snapshot.chapters)}")
    lines.append(f"- 最新章节: {f'ch{snapshot.latest_chapter:03d}' if snapshot.latest_chapter is not None else '无'}")
    lines.append(f"- 下一章节: ch{snapshot.next_chapter:03d}")
    lines.append(f"- 最近章节: {_format_recent_chapters(snapshot)}")
    lines.append("")
    return "\n".join(lines).rstrip()


def _render_active_foreshadowing(snapshot: ProjectSnapshot) -> str:
    active_entries = [entry for entry in snapshot.foreshadowing_entries if entry.section == "Active"]
    if not active_entries:
        return "- 无。"

    lines: list[str] = []
    for entry in active_entries:
        lines.append(
            f"- {entry.entry_id}: {entry.description}"
            + (f" | payoff {_format_payoff(entry)}" if entry.planned_payoff is not None else "")
        )
    return "\n".join(lines)


def _render_major_turning_points(snapshot: ProjectSnapshot) -> str:
    if not snapshot.major_turning_points:
        return "- 无。"

    return "\n".join(f"- {entry.event_id}: {entry.event}" for entry in snapshot.major_turning_points)


def _render_a_class_issues(issues: list[StructuralIssue]) -> str:
    high_severity = [issue for issue in issues if issue.severity == "高"]
    if not high_severity:
        return "- 无。"

    lines: list[str] = []
    for issue in high_severity:
        lines.append(f"- {issue.category}: {issue.description}")
    return "\n".join(lines)


def _format_recent_chapters(snapshot: ProjectSnapshot) -> str:
    if not snapshot.recent_chapters:
        return "无"
    return ", ".join(f"ch{chapter.number:03d}" for chapter in snapshot.recent_chapters[:5])


def _format_payoff(entry) -> str:
    payoff = entry.planned_payoff
    if payoff is None:
        return "unknown"
    if payoff.open_ended:
        return f"ch{payoff.start_chapter:03d}+"
    if payoff.end_chapter is None or payoff.end_chapter == payoff.start_chapter:
        return f"ch{payoff.start_chapter:03d}"
    return f"ch{payoff.start_chapter:03d}-ch{payoff.end_chapter:03d}"


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _read_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""
