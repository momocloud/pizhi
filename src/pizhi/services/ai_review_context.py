from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.domain.foreshadowing import ForeshadowingEntry
from pizhi.domain.project_state import ChapterState
from pizhi.domain.project_state import ProjectSnapshot
from pizhi.services.consistency.structural import StructuralIssue
from pizhi.services.consistency.structural import StructuralReport
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.maintenance import format_maintenance_summary
from pizhi.services.project_snapshot import load_project_snapshot


CHARACTER_INDEX_ENTRY_RE = re.compile(r"^## (?P<name>.+?)\s*$", re.MULTILINE)
CHARACTER_INDEX_ALIAS_RE = re.compile(r"^- \*\*(?:别名|Alias|Aliases)\*\*[:：]\s*(?P<value>.+)$")
CHARACTER_INDEX_SEPARATOR_RE = re.compile(r"[，,、/|]")

CHAPTER_TEXT_CHAR_LIMIT = 4000
CHAPTER_SUPPORTING_TEXT_CHAR_LIMIT = 1800
WORLDVIEW_CHAR_LIMIT = 2500
CHARACTER_INDEX_ENTRY_CHAR_LIMIT = 1200
CHARACTER_INDEX_ENTRY_LIMIT = 6
CHAPTER_FORESHADOWING_LIMIT = 8
STRUCTURAL_ISSUE_LIMIT = 12
FULL_SECTION_ITEM_LIMIT = 12
FULL_CHAPTER_SIGNAL_SUMMARY_CHAR_LIMIT = 240
FULL_METADATA_CHAPTER_LIMIT = 5
METADATA_NAME_LIMIT = 8
METADATA_ID_LIMIT = 10
MAINTENANCE_SUMMARY_CHAR_LIMIT = 2000


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

    current_meta = _load_json(chapter_dir / "meta.json")
    previous_meta = _load_json(previous_dir / "meta.json") if previous_dir is not None else {}
    current_characters = _read_text(chapter_dir / "characters.md")
    current_relationships = _read_text(chapter_dir / "relationships.md")
    previous_text = _read_text(previous_dir / "text.md") if previous_dir is not None else ""
    previous_characters = _read_text(previous_dir / "characters.md") if previous_dir is not None else ""
    previous_relationships = _read_text(previous_dir / "relationships.md") if previous_dir is not None else ""
    worldview_text = _read_text(paths.worldview_file)
    character_index_raw = _read_text(paths.global_dir / "characters_index.md")
    character_alias_map = _build_character_alias_map(character_index_raw)

    involved_names = _collect_relevant_character_names(current_meta, previous_meta)
    canonical_names = _canonicalize_character_names(involved_names, character_alias_map)
    relevant_foreshadowing = _select_relevant_foreshadowing(
        snapshot,
        current_meta,
        previous_meta,
        canonical_names,
        character_alias_map,
    )
    character_index_text = _render_character_index(character_index_raw, canonical_names, character_alias_map)

    prompt_context = "\n".join(
        [
            "# Chapter AI Review Context",
            "",
            "## 当前章节正文",
            "",
            _truncate_text(_read_text(chapter_dir / "text.md"), CHAPTER_TEXT_CHAR_LIMIT) or "（缺失）",
            "",
            "## 当前角色快照",
            "",
            _truncate_text(current_characters, CHAPTER_SUPPORTING_TEXT_CHAR_LIMIT) or "（缺失）",
            "",
            "## 当前关系快照",
            "",
            _truncate_text(current_relationships, CHAPTER_SUPPORTING_TEXT_CHAR_LIMIT) or "（缺失）",
            "",
            "## 关键 meta 摘要",
            "",
            _render_meta_summary(current_meta),
            "",
            "## 上一章正文",
            "",
            _truncate_text(previous_text, CHAPTER_TEXT_CHAR_LIMIT) or "（无上一章）",
            "",
            "## 上一章角色快照",
            "",
            _truncate_text(previous_characters, CHAPTER_SUPPORTING_TEXT_CHAR_LIMIT) or "（无上一章）",
            "",
            "## 上一章关系快照",
            "",
            _truncate_text(previous_relationships, CHAPTER_SUPPORTING_TEXT_CHAR_LIMIT) or "（无上一章）",
            "",
            "## 世界观",
            "",
            _truncate_text(worldview_text, WORLDVIEW_CHAR_LIMIT) or "（无世界观内容）",
            "",
            "## 相关伏笔",
            "",
            _render_foreshadowing(relevant_foreshadowing),
            "",
            "## 角色索引",
            "",
            character_index_text,
            "",
            "## A 类结构问题",
            "",
            _render_structural_issues(structural_issues),
        ]
    ).rstrip() + "\n"

    referenced_files = [
        _relative_path(project_root, chapter_dir / "text.md"),
        _relative_path(project_root, chapter_dir / "characters.md"),
        _relative_path(project_root, chapter_dir / "relationships.md"),
        _relative_path(project_root, chapter_dir / "meta.json"),
        _relative_path(project_root, paths.worldview_file),
        _relative_path(project_root, paths.foreshadowing_file),
        _relative_path(project_root, paths.global_dir / "characters_index.md"),
    ]
    if previous_dir is not None:
        referenced_files.extend(
            [
                _relative_path(project_root, previous_dir / "text.md"),
                _relative_path(project_root, previous_dir / "characters.md"),
                _relative_path(project_root, previous_dir / "relationships.md"),
            ]
        )

    metadata: dict[str, object] = {
        "scope": "chapter",
        "chapter": chapter_number,
        "target_chapter": f"ch{chapter_number:03d}",
        "issue_count": len(structural_issues),
        "relevant_character_names": _limit_values(involved_names, METADATA_NAME_LIMIT),
        "relevant_character_count": len(involved_names),
        "relevant_foreshadowing_ids": _limit_values([entry.entry_id for entry in relevant_foreshadowing], METADATA_ID_LIMIT),
        "relevant_foreshadowing_count": len(relevant_foreshadowing),
    }
    if current_meta:
        metadata["chapter_title"] = current_meta.get("chapter_title")
        metadata["word_count_estimated"] = current_meta.get("word_count_estimated")
        metadata["worldview_changed"] = current_meta.get("worldview_changed")
        metadata["synopsis_changed"] = current_meta.get("synopsis_changed")
        current_characters_involved = [str(name) for name in current_meta.get("characters_involved", [])]
        metadata["characters_involved"] = _limit_values(current_characters_involved, METADATA_NAME_LIMIT)
        metadata["characters_involved_count"] = len(current_characters_involved)

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
            "",
            "## A 类全书问题",
            "",
            _render_structural_issues(report.global_issues),
            "",
            "## 章节问题摘要",
            "",
            _render_chapter_issue_summary(report),
            "",
            "## 活跃伏笔",
            "",
            _render_active_foreshadowing(snapshot),
            "",
            "## 超期伏笔",
            "",
            _render_overdue_foreshadowing(snapshot),
            "",
            "## 重大转折",
            "",
            _render_major_turning_points(snapshot),
            "",
            "## 最近章节状态",
            "",
            _render_recent_chapter_status(snapshot),
            "",
            "## 章节信号",
            "",
            _render_chapter_signals(snapshot),
            "",
            _render_maintenance_summary(maintenance_result),
        ]
    ).rstrip() + "\n"

    referenced_files = [
        _relative_path(project_root, paths.synopsis_file),
        _relative_path(project_root, paths.worldview_file),
        _relative_path(project_root, paths.timeline_file),
        _relative_path(project_root, paths.foreshadowing_file),
        _relative_path(project_root, paths.global_dir / "characters_index.md"),
    ]
    for chapter in snapshot.recent_chapters[:3]:
        referenced_files.extend(
            [
                _relative_path(project_root, chapter.chapter_dir / "text.md"),
                _relative_path(project_root, chapter.chapter_dir / "characters.md"),
                _relative_path(project_root, chapter.chapter_dir / "relationships.md"),
            ]
        )

    metadata: dict[str, object] = {
        "scope": "full",
        "chapters_reviewed": report.chapters_reviewed,
        "chapter_issues": report.total_chapter_issues,
        "global_issues": len(report.global_issues),
        "active_foreshadowing": len(_active_foreshadowing_entries(snapshot)),
        "overdue_foreshadowing": len(_overdue_foreshadowing_entries(snapshot)),
        "recent_chapter_count": len(snapshot.recent_chapters),
        "recent_chapter_targets": [
            f"ch{chapter.number:03d}" for chapter in snapshot.recent_chapters[:FULL_METADATA_CHAPTER_LIMIT]
        ],
        "maintenance_findings": len(maintenance_result.findings),
    }

    return AIReviewContext(
        scope="full",
        target="project",
        prompt_context=prompt_context,
        referenced_files=referenced_files,
        metadata=metadata,
    )


def _render_project_snapshot(snapshot: ProjectSnapshot) -> str:
    lines = ["## 项目快照", ""]
    lines.append(f"- 项目名称: {snapshot.project_name}")
    lines.append(f"- 已记录章节: {len(snapshot.chapters)}")
    lines.append(f"- 最新章节: {f'ch{snapshot.latest_chapter:03d}' if snapshot.latest_chapter is not None else '无'}")
    lines.append(f"- 下一章节: ch{snapshot.next_chapter:03d}")
    lines.append(f"- 最近章节: {_format_recent_chapters(snapshot)}")
    return "\n".join(lines)


def _render_meta_summary(meta: dict[str, object]) -> str:
    if not meta:
        return "- 无。"

    lines = ["- chapter_title: " + str(meta.get("chapter_title", ""))]
    lines.append("- word_count_estimated: " + str(meta.get("word_count_estimated", "")))
    lines.append("- characters_involved: " + ", ".join(str(name) for name in meta.get("characters_involved", [])))
    lines.append("- worldview_changed: " + str(meta.get("worldview_changed", "")))
    lines.append("- synopsis_changed: " + str(meta.get("synopsis_changed", "")))
    lines.append("- timeline_events: " + str(len(meta.get("timeline_events", []))))
    foreshadowing = meta.get("foreshadowing", {})
    if isinstance(foreshadowing, dict):
        introduced = len(foreshadowing.get("introduced", []))
        referenced = len(foreshadowing.get("referenced", []))
        resolved = len(foreshadowing.get("resolved", []))
        lines.append(f"- foreshadowing: introduced={introduced}, referenced={referenced}, resolved={resolved}")
    review_context = meta.get("review_context", {})
    if isinstance(review_context, dict):
        lines.append("- review_context.previous_last_non_flashback: " + str(review_context.get("previous_last_non_flashback", "")))
    return "\n".join(lines)


def _render_foreshadowing(entries: list[ForeshadowingEntry]) -> str:
    if not entries:
        return "- 无。"

    lines: list[str] = []
    for entry in entries[:CHAPTER_FORESHADOWING_LIMIT]:
        lines.append(
            f"- {entry.entry_id} [{entry.section}]: {entry.description}"
            + (f" | payoff {_format_payoff(entry)}" if entry.planned_payoff is not None else "")
        )
    _append_truncation_line(lines, len(entries), CHAPTER_FORESHADOWING_LIMIT)
    return "\n".join(lines)


def _render_structural_issues(issues: list[StructuralIssue]) -> str:
    if not issues:
        return "- 无。"

    lines: list[str] = []
    for issue in issues[:STRUCTURAL_ISSUE_LIMIT]:
        lines.append(
            f"- {issue.category} ({issue.severity}): {issue.description}"
        )
    _append_truncation_line(lines, len(issues), STRUCTURAL_ISSUE_LIMIT)
    return "\n".join(lines)


def _render_character_index(raw_index: str, relevant_names: set[str], alias_map: dict[str, str]) -> str:
    if not raw_index.strip() or not relevant_names:
        return "- 无。"

    blocks = list(CHARACTER_INDEX_ENTRY_RE.finditer(raw_index))
    if not blocks:
        return "- 无。"

    rendered: list[str] = []
    for index, match in enumerate(blocks):
        name = match.group("name").strip()
        start = match.start()
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(raw_index)
        block_text = raw_index[start:end].strip()
        aliases = _extract_character_aliases(block_text)
        canonical_name = alias_map.get(name, name)
        if canonical_name not in relevant_names and not relevant_names.intersection(aliases):
            continue
        rendered.append(_truncate_text(block_text, CHARACTER_INDEX_ENTRY_CHAR_LIMIT))
    if not rendered:
        return "- 无。"

    visible_blocks = rendered[:CHARACTER_INDEX_ENTRY_LIMIT]
    if len(rendered) > CHARACTER_INDEX_ENTRY_LIMIT:
        visible_blocks.append(f"... [truncated {len(rendered) - CHARACTER_INDEX_ENTRY_LIMIT} more entries]")
    return "\n\n".join(visible_blocks)


def _select_relevant_foreshadowing(
    snapshot: ProjectSnapshot,
    current_meta: dict[str, object],
    previous_meta: dict[str, object],
    canonical_names: set[str],
    alias_map: dict[str, str],
) -> list[ForeshadowingEntry]:
    relevant_ids = _foreshadowing_ids_from_meta(current_meta) | _foreshadowing_ids_from_meta(previous_meta)
    relevant: list[ForeshadowingEntry] = []
    for entry in snapshot.foreshadowing_entries:
        if entry.section not in {"Active", "Referenced"}:
            continue
        if entry.entry_id in relevant_ids:
            relevant.append(entry)
            continue
        if canonical_names.intersection(_canonicalize_character_names(entry.related_characters, alias_map)):
            relevant.append(entry)
    return relevant


def _foreshadowing_ids_from_meta(meta: dict[str, object]) -> set[str]:
    if not meta:
        return set()

    foreshadowing = meta.get("foreshadowing", {})
    if not isinstance(foreshadowing, dict):
        return set()

    ids: set[str] = set()
    for section_name in ("introduced", "referenced", "resolved"):
        for item in foreshadowing.get(section_name, []):
            if isinstance(item, dict) and "id" in item:
                ids.add(str(item["id"]))
    return ids


def _collect_relevant_character_names(
    current_meta: dict[str, object],
    previous_meta: dict[str, object],
) -> list[str]:
    names: set[str] = set()
    for meta in (current_meta, previous_meta):
        involved = meta.get("characters_involved", [])
        if isinstance(involved, list):
            names.update(str(name) for name in involved if str(name).strip())
    return sorted(names)


def _build_character_alias_map(raw_index: str) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    blocks = list(CHARACTER_INDEX_ENTRY_RE.finditer(raw_index))
    for index, match in enumerate(blocks):
        canonical_name = match.group("name").strip()
        start = match.start()
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(raw_index)
        block_text = raw_index[start:end].strip()
        alias_map[canonical_name] = canonical_name
        for alias in _extract_character_aliases(block_text):
            alias_map[alias] = canonical_name
    return alias_map


def _canonicalize_character_names(names: set[str] | list[str], alias_map: dict[str, str]) -> set[str]:
    canonical_names: set[str] = set()
    for name in names:
        stripped = str(name).strip()
        if not stripped:
            continue
        canonical_names.add(alias_map.get(stripped, stripped))
    return canonical_names


def _extract_character_aliases(block_text: str) -> set[str]:
    aliases: set[str] = set()
    for line in block_text.splitlines():
        match = CHARACTER_INDEX_ALIAS_RE.fullmatch(line.strip())
        if match is None:
            continue
        for alias in CHARACTER_INDEX_SEPARATOR_RE.split(match.group("value")):
            alias = alias.strip()
            if alias:
                aliases.add(alias)
    return aliases


def _render_active_foreshadowing(snapshot: ProjectSnapshot) -> str:
    active_entries = _active_foreshadowing_entries(snapshot)
    if not active_entries:
        return "- 无。"

    lines = [
        f"- {entry.entry_id}: {entry.description}"
        + (f" | payoff {_format_payoff(entry)}" if entry.planned_payoff is not None else "")
        for entry in active_entries[:FULL_SECTION_ITEM_LIMIT]
    ]
    _append_truncation_line(lines, len(active_entries), FULL_SECTION_ITEM_LIMIT)
    return "\n".join(lines)


def _render_overdue_foreshadowing(snapshot: ProjectSnapshot) -> str:
    overdue_entries = _overdue_foreshadowing_entries(snapshot)
    if not overdue_entries:
        return "- 无。"

    lines = [
        f"- {entry.entry_id}: {entry.description} | {_format_payoff(entry)}"
        for entry in overdue_entries[:FULL_SECTION_ITEM_LIMIT]
    ]
    _append_truncation_line(lines, len(overdue_entries), FULL_SECTION_ITEM_LIMIT)
    return "\n".join(lines)


def _active_foreshadowing_entries(snapshot: ProjectSnapshot) -> list[ForeshadowingEntry]:
    return [entry for entry in snapshot.foreshadowing_entries if entry.section == "Active"]


def _overdue_foreshadowing_entries(snapshot: ProjectSnapshot) -> list[ForeshadowingEntry]:
    overdue: list[ForeshadowingEntry] = []
    for entry in snapshot.foreshadowing_entries:
        if entry.section not in {"Active", "Referenced"}:
            continue
        if not _is_overdue(entry, snapshot.next_chapter):
            continue
        overdue.append(entry)
    return overdue


def _render_major_turning_points(snapshot: ProjectSnapshot) -> str:
    if not snapshot.major_turning_points:
        return "- 无。"

    visible_points = snapshot.major_turning_points[-FULL_SECTION_ITEM_LIMIT:]
    lines = [f"- {entry.event_id}: {entry.event}" for entry in visible_points]
    _append_truncation_line(lines, len(snapshot.major_turning_points), FULL_SECTION_ITEM_LIMIT)
    return "\n".join(lines)


def _render_recent_chapter_status(snapshot: ProjectSnapshot) -> str:
    if not snapshot.recent_chapters:
        return "- 无。"

    lines: list[str] = []
    for chapter in snapshot.recent_chapters[:FULL_METADATA_CHAPTER_LIMIT]:
        lines.append(
            f"- ch{chapter.number:03d} [{chapter.status}]: {chapter.title}"
        )
    return "\n".join(lines)


def _render_chapter_signals(snapshot: ProjectSnapshot) -> str:
    if not snapshot.chapters:
        return "- 无。"

    lines: list[str] = []
    chapter_numbers = sorted(snapshot.chapters, reverse=True)
    for chapter_number in chapter_numbers[:FULL_SECTION_ITEM_LIMIT]:
        chapter = snapshot.chapters[chapter_number]
        lines.append(
            f"- ch{chapter.number:03d} [{chapter.status}]: "
            f"{_truncate_text(chapter.summary or '无摘要', FULL_CHAPTER_SIGNAL_SUMMARY_CHAR_LIMIT)}"
        )
    _append_truncation_line(lines, len(chapter_numbers), FULL_SECTION_ITEM_LIMIT)
    return "\n".join(lines)


def _render_chapter_issue_summary(report: StructuralReport) -> str:
    if not report.chapter_issues:
        return "- 无。"

    lines: list[str] = []
    chapter_numbers = sorted(report.chapter_issues, reverse=True)
    for chapter_number in chapter_numbers[:FULL_SECTION_ITEM_LIMIT]:
        issues = report.chapter_issues[chapter_number]
        if not issues:
            lines.append(f"- ch{chapter_number:03d}: 0 issues")
            continue
        categories = ", ".join(issue.category for issue in issues[:FULL_METADATA_CHAPTER_LIMIT])
        if len(issues) > FULL_METADATA_CHAPTER_LIMIT:
            categories += f", ... [{len(issues) - FULL_METADATA_CHAPTER_LIMIT} more]"
        lines.append(f"- ch{chapter_number:03d}: {len(issues)} issues [{categories}]")
    _append_truncation_line(lines, len(chapter_numbers), FULL_SECTION_ITEM_LIMIT)
    return "\n".join(lines)


def _format_recent_chapters(snapshot: ProjectSnapshot) -> str:
    if not snapshot.recent_chapters:
        return "无"
    return ", ".join(f"ch{chapter.number:03d}" for chapter in snapshot.recent_chapters[:FULL_METADATA_CHAPTER_LIMIT])


def _format_payoff(entry: ForeshadowingEntry) -> str:
    payoff = entry.planned_payoff
    if payoff is None:
        return "unknown"
    if payoff.open_ended:
        return f"ch{payoff.start_chapter:03d}+"
    if payoff.end_chapter is None or payoff.end_chapter == payoff.start_chapter:
        return f"ch{payoff.start_chapter:03d}"
    return f"ch{payoff.start_chapter:03d}-ch{payoff.end_chapter:03d}"


def _is_overdue(entry: ForeshadowingEntry, next_chapter: int) -> bool:
    if entry.planned_payoff is None:
        return False
    if entry.planned_payoff.open_ended:
        return False
    deadline = entry.planned_payoff.end_chapter or entry.planned_payoff.start_chapter
    return deadline < next_chapter


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        return dict(json.loads(raw))
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _read_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _truncate_text(text: str, max_chars: int) -> str:
    if not text:
        return ""
    normalized = text.strip()
    if len(normalized) <= max_chars:
        return normalized
    truncated = normalized[:max_chars].rstrip()
    return f"{truncated}\n... [truncated {len(normalized) - len(truncated)} chars]"


def _append_truncation_line(lines: list[str], total_count: int, visible_count: int) -> None:
    if total_count > visible_count:
        lines.append(f"- ... [truncated {total_count - visible_count} more items]")


def _limit_values(values: list[str], limit: int) -> list[str]:
    if len(values) <= limit:
        return list(values)
    limited = list(values[:limit])
    limited.append(f"... [{len(values) - limit} more]")
    return limited


def _render_maintenance_summary(maintenance_result: MaintenanceResult) -> str:
    return _truncate_text(format_maintenance_summary(maintenance_result).rstrip(), MAINTENANCE_SUMMARY_CHAR_LIMIT)
