from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

from pizhi.core.config import load_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.domain.foreshadowing import tracker_ids_by_section
from pizhi.domain.foreshadowing import update_foreshadowing_tracker
from pizhi.domain.timeline import append_timeline_events
from pizhi.domain.timeline import parse_timeline_entries
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
    previous_last_non_flashback = _previous_last_non_flashback(paths, timeline_current)
    timeline_updated = append_timeline_events(timeline_current, chapter_number, parsed.metadata.timeline_events)
    _write_text(paths.timeline_file, timeline_updated)

    foreshadowing_current = _read_text(
        paths.foreshadowing_file,
        "# Foreshadowing Tracker\n\n## Active\n\n## Referenced\n\n## Resolved\n\n## Abandoned\n",
    )
    foreshadowing_ids_before = tracker_ids_by_section(foreshadowing_current)
    foreshadowing_updated = update_foreshadowing_tracker(
        foreshadowing_current,
        parsed.metadata.foreshadowing,
        chapter_number=chapter_number,
    )
    _write_text(paths.foreshadowing_file, foreshadowing_updated)

    if parsed.metadata.synopsis_changed and parsed.sections.synopsis_new:
        _write_text(paths.synopsis_candidate_file, parsed.sections.synopsis_new + "\n")

    _write_text(
        paths.last_session_file,
        f"# Last Session\n\n- Last chapter: ch{chapter_number:03d}\n- Title: {parsed.metadata.chapter_title}\n",
    )
    _write_text(
        chapter_dir / "meta.json",
        json.dumps(
            {
                "chapter_title": parsed.metadata.chapter_title,
                "word_count_estimated": parsed.metadata.word_count_estimated,
                "characters_involved": parsed.metadata.characters_involved,
                "worldview_changed": parsed.metadata.worldview_changed,
                "synopsis_changed": parsed.metadata.synopsis_changed,
                "timeline_events": parsed.metadata.timeline_events,
                "foreshadowing": parsed.metadata.foreshadowing,
                "review_context": {
                    "previous_last_non_flashback": previous_last_non_flashback,
                    "active_foreshadowing_ids": sorted(foreshadowing_ids_before["Active"]),
                    "referenced_foreshadowing_ids": sorted(foreshadowing_ids_before["Referenced"]),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
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


def _previous_last_non_flashback(paths, live_timeline_text: str) -> str | None:
    entries = []
    if paths.archive_dir.exists():
        for archive_path in sorted(paths.archive_dir.glob("timeline_ch*.md")):
            entries.extend(parse_timeline_entries(archive_path.read_text(encoding="utf-8")))
    entries.extend(parse_timeline_entries(live_timeline_text))

    for entry in reversed(entries):
        if not entry.is_flashback:
            return entry.at
    return None
