from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pizhi.core.frontmatter import parse_frontmatter
from pizhi.core.markdown_sections import ChapterSections
from pizhi.core.markdown_sections import split_chapter_sections


@dataclass(slots=True)
class ChapterMetadata:
    chapter_title: str
    word_count_estimated: int
    characters_involved: list[str]
    worldview_changed: bool
    synopsis_changed: bool
    timeline_events: list[dict[str, Any]]
    foreshadowing: dict[str, Any]


@dataclass(slots=True)
class ParsedChapterResponse:
    metadata: ChapterMetadata
    sections: ChapterSections


REQUIRED_KEYS = {
    "chapter_title",
    "word_count_estimated",
    "characters_involved",
    "worldview_changed",
    "synopsis_changed",
    "timeline_events",
    "foreshadowing",
}


def parse_chapter_response(raw: str) -> ParsedChapterResponse:
    metadata_raw, body = parse_frontmatter(raw)
    missing = REQUIRED_KEYS.difference(metadata_raw)
    if missing:
        raise ValueError(f"missing frontmatter keys: {', '.join(sorted(missing))}")

    sections = split_chapter_sections(body)
    metadata = ChapterMetadata(
        chapter_title=_expect_type(metadata_raw["chapter_title"], str, "chapter_title"),
        word_count_estimated=int(metadata_raw["word_count_estimated"]),
        characters_involved=_expect_list_of_str(metadata_raw["characters_involved"], "characters_involved"),
        worldview_changed=bool(metadata_raw["worldview_changed"]),
        synopsis_changed=bool(metadata_raw["synopsis_changed"]),
        timeline_events=_expect_list_of_dict(metadata_raw["timeline_events"], "timeline_events"),
        foreshadowing=_expect_type(metadata_raw["foreshadowing"], dict, "foreshadowing"),
    )

    if metadata.worldview_changed and not sections.worldview_patch:
        raise ValueError("worldview_patch section is required when worldview_changed is true")
    if metadata.synopsis_changed and not sections.synopsis_new:
        raise ValueError("synopsis_new section is required when synopsis_changed is true")

    return ParsedChapterResponse(metadata=metadata, sections=sections)


def _expect_type(value: Any, expected: type, field_name: str) -> Any:
    if not isinstance(value, expected):
        raise ValueError(f"{field_name} must be {expected.__name__}")
    return value


def _expect_list_of_str(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list[str]")
    return value


def _expect_list_of_dict(value: Any, field_name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field_name} must be a list[dict]")
    return value
