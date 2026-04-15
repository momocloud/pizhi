from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.domain.timeline import time_sort_key


@dataclass(slots=True)
class StructuralIssue:
    category: str
    severity: str
    description: str
    evidence: str
    suggestion: str


@dataclass(slots=True)
class StructuralReport:
    issues: list[StructuralIssue]


def run_structural_review(project_root: Path, chapter_number: int | None = None, full: bool = False) -> StructuralReport:
    paths = project_paths(project_root)
    records = ChapterIndexStore(paths.chapter_index_file).read_all()
    if full:
        targets = [int(record["n"]) for record in records]
    else:
        if chapter_number is not None:
            targets = [chapter_number]
        elif records:
            targets = [max(int(record["n"]) for record in records)]
        else:
            targets = []

    all_issues: list[StructuralIssue] = []
    records_by_number = {int(record["n"]): record for record in records}
    for target in targets:
        chapter_issues = _review_chapter(paths, records_by_number, target)
        _write_notes(paths.chapter_dir(target) / "notes.md", chapter_issues)
        all_issues.extend(chapter_issues)
    return StructuralReport(issues=all_issues)


def _review_chapter(paths, records_by_number: dict[int, dict], chapter_number: int) -> list[StructuralIssue]:
    issues: list[StructuralIssue] = []
    chapter_dir = paths.chapter_dir(chapter_number)

    text_path = chapter_dir / "text.md"
    characters_path = chapter_dir / "characters.md"
    relationships_path = chapter_dir / "relationships.md"
    meta_path = chapter_dir / "meta.json"

    for required_path in (text_path, characters_path, relationships_path, meta_path):
        if not required_path.exists() or not required_path.read_text(encoding="utf-8").strip():
            issues.append(
                StructuralIssue(
                    category="文件完整性",
                    severity="高",
                    description=f"{required_path.name} 缺失或为空。",
                    evidence=str(required_path),
                    suggestion="重新生成该章节并确认必要文件都已写入。",
                )
            )

    if issues and not meta_path.exists():
        return issues

    if chapter_number > 1 and (chapter_number - 1) not in records_by_number:
        issues.append(
            StructuralIssue(
                category="章节号连续性",
                severity="高",
                description=f"第 {chapter_number} 章存在，但上一章记录缺失。",
                evidence=f"index.jsonl 中未找到章节 {chapter_number - 1}",
                suggestion="先补齐缺失章节，再继续生成后续内容。",
            )
        )

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    text = text_path.read_text(encoding="utf-8")
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
