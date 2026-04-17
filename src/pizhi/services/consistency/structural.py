from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from pizhi.core.paths import project_paths
from pizhi.domain.foreshadowing import ForeshadowingEntry
from pizhi.domain.timeline import time_sort_key
from pizhi.services.project_snapshot import load_project_snapshot

ADVANCED_CHAPTER_STATUSES = {"drafted", "reviewed", "compiled"}
TRACKED_FORESHADOWING_SECTIONS = {"Active", "Referenced"}
CHAPTER_DIR_RE = re.compile(r"^ch(?P<number>\d{3})$")
REQUIRED_ARTIFACT_NAMES = ("text.md", "characters.md", "relationships.md", "meta.json")


@dataclass(slots=True)
class StructuralIssue:
    category: str
    severity: str
    description: str
    evidence: str
    suggestion: str


@dataclass(slots=True)
class StructuralReport:
    chapter_issues: dict[int, list[StructuralIssue]]
    global_issues: list[StructuralIssue]

    @property
    def issues(self) -> list[StructuralIssue]:
        combined: list[StructuralIssue] = []
        for issues in self.chapter_issues.values():
            combined.extend(issues)
        combined.extend(self.global_issues)
        return combined

    @property
    def chapters_reviewed(self) -> int:
        return len(self.chapter_issues)

    @property
    def chapters_with_issues(self) -> int:
        return sum(1 for issues in self.chapter_issues.values() if issues)

    @property
    def total_chapter_issues(self) -> int:
        return sum(len(issues) for issues in self.chapter_issues.values())

    @property
    def total_issues(self) -> int:
        return self.total_chapter_issues + len(self.global_issues)


def run_structural_review(project_root: Path, chapter_number: int | None = None, full: bool = False) -> StructuralReport:
    snapshot = load_project_snapshot(project_root)
    paths = project_paths(project_root)
    targets = _select_targets(snapshot, chapter_number, full)

    chapter_issues: dict[int, list[StructuralIssue]] = {}
    for target in targets:
        issues = _review_chapter(snapshot, paths, target)
        chapter_issues[target] = issues
        _write_notes(paths.chapter_dir(target) / "notes.md", issues)

    global_issues = _review_project(snapshot, paths) if full else []
    return StructuralReport(
        chapter_issues=chapter_issues,
        global_issues=global_issues,
    )


def format_structural_report(report: StructuralReport) -> str:
    lines = [
        "# Structural Review",
        "",
        f"- Chapters reviewed: {report.chapters_reviewed}",
        f"- Chapters with issues: {report.chapters_with_issues}",
        f"- Chapter issues: {report.total_chapter_issues}",
        f"- Global issues: {len(report.global_issues)}",
        "",
        "## Global issues:",
        "",
    ]

    if not report.global_issues:
        lines.append("- None.")
        lines.append("")
    else:
        lines.extend(_format_issue_list(report.global_issues))

    for chapter_number, issues in report.chapter_issues.items():
        lines.append(f"## ch{chapter_number:03d}")
        lines.append("")
        if not issues:
            lines.append("- None.")
            lines.append("")
            continue
        lines.extend(_format_issue_list(issues))

    return "\n".join(lines).rstrip() + "\n"


def _select_targets(snapshot, chapter_number: int | None, full: bool) -> list[int]:
    if full:
        return sorted(snapshot.chapters)
    if chapter_number is not None:
        return [chapter_number]
    if snapshot.latest_chapter is None:
        return []
    return [snapshot.latest_chapter]


def _review_chapter(snapshot, paths, chapter_number: int) -> list[StructuralIssue]:
    chapter = snapshot.chapters.get(chapter_number)
    chapter_dir = paths.chapter_dir(chapter_number)
    issues: list[StructuralIssue] = []

    for artifact_name in REQUIRED_ARTIFACT_NAMES:
        artifact_path = chapter_dir / artifact_name
        if not _path_has_content(artifact_path):
            issues.append(
                StructuralIssue(
                    category="文件完整性",
                    severity="高",
                    description=f"{artifact_name} 缺失或为空。",
                    evidence=str(artifact_path),
                    suggestion="重新生成该章节并确认必要文件都已写入。",
                )
            )

    meta_path = chapter_dir / "meta.json"
    if not meta_path.exists():
        return issues

    metadata = chapter.metadata if chapter is not None else _load_json(meta_path)
    text = _read_text(chapter_dir / "text.md")

    for character_name in metadata.get("characters_involved", []):
        if character_name not in text:
            issues.append(
                StructuralIssue(
                    category="出场角色一致性",
                    severity="中",
                    description=f"frontmatter 声明了角色 {character_name}，但正文中未出现该名字。",
                    evidence=f"{character_name} 不在 text.md 中",
                    suggestion="补写该角色的实际出场，或从 metadata 中移除。",
                )
            )

    previous_last = metadata.get("review_context", {}).get("previous_last_non_flashback")
    last_time = previous_last
    for event in metadata.get("timeline_events", []):
        if event.get("is_flashback"):
            continue
        current_time = event["at"]
        if last_time is not None and time_sort_key(current_time) < time_sort_key(last_time):
            issues.append(
                StructuralIssue(
                    category="时间线单调性",
                    severity="高",
                    description=f"第 {chapter_number} 章的非闪回事件时间早于上一条非闪回事件。",
                    evidence=f"{current_time} < {last_time}",
                    suggestion="调整事件时间或将该事件显式标记为闪回。",
                )
            )
            break
        last_time = current_time

    resolved_ids = {
        item["id"]
        for item in metadata.get("foreshadowing", {}).get("resolved", [])
        if isinstance(item, dict) and "id" in item
    }
    available_ids = set(metadata.get("review_context", {}).get("active_foreshadowing_ids", []))
    available_ids.update(metadata.get("review_context", {}).get("referenced_foreshadowing_ids", []))
    for resolved_id in sorted(resolved_ids):
        if resolved_id not in available_ids:
            issues.append(
                StructuralIssue(
                    category="伏笔 ID 引用合法性",
                    severity="高",
                    description=f"resolved 中引用的 {resolved_id} 在写入前不在 active/referenced 中。",
                    evidence=f"available ids: {sorted(available_ids)}",
                    suggestion="只回收已激活或已引用的伏笔，或先在前文埋设该 ID。",
                )
            )

    return issues


def _review_project(snapshot, paths) -> list[StructuralIssue]:
    issues: list[StructuralIssue] = []
    issues.extend(_find_index_directory_mismatches(snapshot, paths))
    issues.extend(_find_advanced_artifact_gaps(snapshot))
    issues.extend(_find_chapter_number_gaps(snapshot))
    issues.extend(_find_overdue_foreshadowing(snapshot))
    return issues


def _find_index_directory_mismatches(snapshot, paths) -> list[StructuralIssue]:
    indexed_numbers = set(snapshot.chapters)
    chapter_dirs = set(_discover_chapter_directories(paths))
    missing_directories = sorted(number for number in indexed_numbers if not snapshot.chapters[number].chapter_dir.exists())
    missing_index_entries = sorted(number for number in chapter_dirs if number not in indexed_numbers)

    issues: list[StructuralIssue] = []
    if missing_directories:
        issues.append(
            StructuralIssue(
                category="章节索引/目录不一致",
                severity="高",
                description="chapter index 中存在章节，但对应目录缺失。",
                evidence=f"index only: {_format_chapter_list(missing_directories)}",
                suggestion="补回缺失目录，或清理错误的章节索引记录。",
            )
        )
    if missing_index_entries:
        issues.append(
            StructuralIssue(
                category="章节索引/目录不一致",
                severity="高",
                description="章节目录存在，但 chapter index 中缺少对应记录。",
                evidence=f"directory only: {_format_chapter_list(missing_index_entries)}",
                suggestion="补写章节索引记录，或清理不应存在的目录。",
            )
        )
    return issues


def _find_advanced_artifact_gaps(snapshot) -> list[StructuralIssue]:
    issues: list[StructuralIssue] = []
    for chapter in snapshot.chapters.values():
        if chapter.status not in ADVANCED_CHAPTER_STATUSES:
            continue
        missing_artifacts = _missing_artifacts(chapter.chapter_dir)
        if not missing_artifacts:
            continue
        issues.append(
            StructuralIssue(
                category="章节产物缺失",
                severity="高",
                description=f"ch{chapter.number:03d} 已处于 {chapter.status} 状态，但缺少必要产物。",
                evidence=", ".join(missing_artifacts),
                suggestion="重新生成或补齐章节产物，再保留该进度状态。",
            )
        )
    return issues


def _find_chapter_number_gaps(snapshot) -> list[StructuralIssue]:
    chapter_numbers = sorted(snapshot.chapters)
    if len(chapter_numbers) < 2:
        return []

    missing_numbers: list[int] = []
    for current, following in zip(chapter_numbers, chapter_numbers[1:], strict=False):
        if following - current <= 1:
            continue
        missing_numbers.extend(range(current + 1, following))

    if not missing_numbers:
        return []

    return [
        StructuralIssue(
            category="章节号缺口",
            severity="高",
            description="已记录章节之间存在明显断号。",
            evidence=_format_chapter_list(missing_numbers),
            suggestion="确认这些章节是尚未建立、被误删，还是 index 记录存在跳号。",
        )
    ]


def _find_overdue_foreshadowing(snapshot) -> list[StructuralIssue]:
    issues: list[StructuralIssue] = []
    for entry in snapshot.foreshadowing_entries:
        if entry.section not in TRACKED_FORESHADOWING_SECTIONS:
            continue
        if not _is_overdue(entry, snapshot.next_chapter):
            continue
        issues.append(
            StructuralIssue(
                category="伏笔超期",
                severity="高",
                description=f"{entry.entry_id} 已超过计划回收窗口，但仍处于 {entry.section}。",
                evidence=f"{_format_payoff_window(entry)}; next chapter: ch{snapshot.next_chapter:03d}",
                suggestion="尽快回收该伏笔，或更新 tracker 中的 planned payoff。",
            )
        )
    return issues


def _discover_chapter_directories(paths) -> list[int]:
    if not paths.chapters_dir.exists():
        return []

    chapter_numbers: list[int] = []
    for path in paths.chapters_dir.iterdir():
        if not path.is_dir():
            continue
        match = CHAPTER_DIR_RE.fullmatch(path.name)
        if match is None:
            continue
        number = int(match.group("number"))
        if number == 0:
            continue
        chapter_numbers.append(number)
    return sorted(chapter_numbers)


def _missing_artifacts(chapter_dir: Path) -> list[str]:
    return [name for name in REQUIRED_ARTIFACT_NAMES if not _path_has_content(chapter_dir / name)]


def _is_overdue(entry: ForeshadowingEntry, next_chapter: int) -> bool:
    if entry.planned_payoff is None:
        return False
    if entry.planned_payoff.open_ended:
        return False
    deadline = entry.planned_payoff.end_chapter or entry.planned_payoff.start_chapter
    return deadline < next_chapter


def _format_payoff_window(entry: ForeshadowingEntry) -> str:
    if entry.planned_payoff is None:
        return "no payoff window"
    start = f"ch{entry.planned_payoff.start_chapter:03d}"
    if entry.planned_payoff.open_ended:
        return f"planned payoff: {start}+"
    end = entry.planned_payoff.end_chapter or entry.planned_payoff.start_chapter
    if end == entry.planned_payoff.start_chapter:
        return f"planned payoff: {start}"
    return f"planned payoff: {start}-ch{end:03d}"


def _format_chapter_list(numbers: list[int]) -> str:
    return ", ".join(f"ch{number:03d}" for number in numbers)


def _format_issue_list(issues: list[StructuralIssue]) -> list[str]:
    lines: list[str] = []
    for index, issue in enumerate(issues, start=1):
        lines.extend(
            [
                f"### Issue {index}",
                f"- Category: {issue.category}",
                f"- Severity: {issue.severity}",
                f"- Description: {issue.description}",
                f"- Evidence: {issue.evidence}",
                f"- Suggestion: {issue.suggestion}",
                "",
            ]
        )
    return lines


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _path_has_content(path: Path) -> bool:
    return path.exists() and bool(path.read_text(encoding="utf-8").strip())


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_notes(path: Path, issues: list[StructuralIssue]) -> None:
    lines = ["## 一致性检查结果", ""]
    if not issues:
        lines.append("- 未发现结构化问题。")
    else:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
