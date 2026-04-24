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
        timeline_events=_expect_timeline_events(metadata_raw["timeline_events"]),
        foreshadowing=_expect_foreshadowing(metadata_raw["foreshadowing"]),
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


def _expect_timeline_events(value: Any) -> list[dict[str, Any]]:
    events = _expect_list_of_dict(value, "timeline_events")
    validated: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        validated.append(_expect_timeline_event(event, index))
    return validated


def _expect_timeline_event(value: Any, index: int) -> dict[str, Any]:
    field_name = f"timeline_events[{index}]"
    event = _expect_type(value, dict, field_name)
    _expect_event_keys(
        event,
        field_name,
        required_keys=("at", "event", "is_flashback", "is_major_turning_point"),
    )
    return {
        "at": _expect_type(event["at"], str, f"{field_name}.at"),
        "event": _expect_type(event["event"], str, f"{field_name}.event"),
        "is_flashback": _expect_type(event["is_flashback"], bool, f"{field_name}.is_flashback"),
        "is_major_turning_point": _expect_type(
            event["is_major_turning_point"], bool, f"{field_name}.is_major_turning_point"
        ),
    }


def _expect_foreshadowing(value: Any) -> dict[str, Any]:
    foreshadowing = _expect_type(value, dict, "foreshadowing")
    _expect_event_keys(
        foreshadowing,
        "foreshadowing",
        required_keys=("introduced", "referenced", "resolved"),
    )
    return {
        "introduced": _expect_foreshadowing_entries(foreshadowing["introduced"], "foreshadowing.introduced"),
        "referenced": _expect_foreshadowing_reference_entries(
            foreshadowing["referenced"], "foreshadowing.referenced"
        ),
        "resolved": _expect_foreshadowing_reference_entries(foreshadowing["resolved"], "foreshadowing.resolved"),
    }


def _expect_foreshadowing_entries(value: Any, field_name: str) -> list[dict[str, Any]]:
    entries = _expect_list_of_dict(value, field_name)
    validated: list[dict[str, Any]] = []
    for index, item in enumerate(entries):
        item_field = f"{field_name}[{index}]"
        _expect_event_keys(
            item,
            item_field,
            required_keys=("id", "desc", "planned_payoff", "priority", "related_characters"),
        )
        validated.append(
            {
                "id": _expect_type(item["id"], str, f"{item_field}.id"),
                "desc": _expect_type(item["desc"], str, f"{item_field}.desc"),
                "planned_payoff": _expect_type(item["planned_payoff"], str, f"{item_field}.planned_payoff"),
                "priority": _expect_type(item["priority"], str, f"{item_field}.priority"),
                "related_characters": _expect_list_of_str(
                    item["related_characters"], f"{item_field}.related_characters"
                ),
            }
        )
    return validated


def _expect_foreshadowing_reference_entries(value: Any, field_name: str) -> list[dict[str, Any]]:
    entries = _expect_list_of_dict(value, field_name)
    validated: list[dict[str, Any]] = []
    for index, item in enumerate(entries):
        item_field = f"{field_name}[{index}]"
        _expect_event_keys(item, item_field, required_keys=("id",))
        validated.append({"id": _expect_type(item["id"], str, f"{item_field}.id")})
    return validated


def _expect_event_keys(value: dict[str, Any], field_name: str, *, required_keys: tuple[str, ...]) -> None:
    missing = [key for key in required_keys if key not in value]
    if missing:
        if len(missing) == 1:
            raise ValueError(f"{field_name} is missing required key: {missing[0]}")
        raise ValueError(f"{field_name} is missing required keys: {', '.join(missing)}")
