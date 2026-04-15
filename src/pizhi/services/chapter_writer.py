from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pizhi.core.config import load_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.domain.foreshadowing import update_foreshadowing_tracker
from pizhi.domain.timeline import append_timeline_events
from pizhi.domain.worldview import apply_worldview_patch
from pizhi.services.chapter_parser import ParsedChapterResponse
from pizhi.services.chapter_parser import parse_chapter_response


@dataclass(slots=True)
class ChapterWriteResult:
    chapter_dir: Path
    parsed: ParsedChapterResponse


def apply_chapter_response(project_root: Path, chapter_number: int, raw_response: str) -> ChapterWriteResult:
    parsed = parse_chapter_response(raw_response)
    paths = project_paths(project_root)
    config = load_config(paths.config_file)
    chapter_dir = paths.chapter_dir(chapter_number)
    chapter_dir.mkdir(parents=True, exist_ok=True)

    _write_text(chapter_dir / "text.md", parsed.sections.body + "\n")
    _write_text(chapter_dir / "characters.md", parsed.sections.characters_snapshot + "\n")
    _write_text(chapter_dir / "relationships.md", parsed.sections.relationships_snapshot + "\n")

    if parsed.sections.worldview_patch:
        _write_text(chapter_dir / "worldview_patch.md", parsed.sections.worldview_patch + "\n")
        worldview_current = _read_text(paths.worldview_file, "# Worldview\n\n")
        worldview_updated = apply_worldview_patch(worldview_current, parsed.sections.worldview_patch)
        _write_text(paths.worldview_file, worldview_updated)

    timeline_current = _read_text(paths.timeline_file, "# Timeline\n\n")
    timeline_updated = append_timeline_events(timeline_current, chapter_number, parsed.metadata.timeline_events)
    _write_text(paths.timeline_file, timeline_updated)

    foreshadowing_current = _read_text(
        paths.foreshadowing_file,
        "# Foreshadowing Tracker\n\n## Active\n\n## Referenced\n\n## Resolved\n\n## Abandoned\n",
    )
    foreshadowing_updated = update_foreshadowing_tracker(foreshadowing_current, parsed.metadata.foreshadowing)
    _write_text(paths.foreshadowing_file, foreshadowing_updated)

    if parsed.metadata.synopsis_changed and parsed.sections.synopsis_new:
        _write_text(paths.synopsis_candidate_file, parsed.sections.synopsis_new + "\n")
        _write_text(
            chapter_dir / "notes.md",
            "## 一致性检查结果\n\n### 问题 1\n- **类别**：Synopsis 覆盖性\n- **严重度**：中\n"
            "- **描述**：已写入 synopsis_candidate.md，等待后续 AI 覆盖性审查后再替换 synopsis.md。\n"
            "- **证据**：当前里程碑仅实现确定性写入，不执行语义覆盖校验。\n"
            "- **建议修法**：在 milestone 3 的 AI review 层完成替换前审查。\n",
        )

    _write_text(
        paths.last_session_file,
        f"# Last Session\n\n- Last chapter: ch{chapter_number:03d}\n- Title: {parsed.metadata.chapter_title}\n",
    )

    summary = " ".join(parsed.sections.body.split())[:100]
    volume = ((chapter_number - 1) // config.chapters.per_volume) + 1
    ChapterIndexStore(paths.chapter_index_file).upsert(
        {
            "n": chapter_number,
            "title": parsed.metadata.chapter_title,
            "vol": volume,
            "status": "drafted",
            "summary": summary,
            "updated": date.today().isoformat(),
        }
    )

    return ChapterWriteResult(chapter_dir=chapter_dir, parsed=parsed)


def _read_text(path: Path, default: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return default


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
