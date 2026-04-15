from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any


PERIOD_ORDER = {
    "凌晨": 1,
    "早晨": 2,
    "上午": 3,
    "中午": 4,
    "下午": 5,
    "傍晚": 6,
    "夜": 7,
}
ENTRY_RE = re.compile(
    r"^## (?P<id>T\d{3}-\d{2})\s*$\n"
    r"- \*\*时间\*\*: (?P<at>.+)\n"
    r"- \*\*事件\*\*: (?P<event>.+)\n"
    r"- \*\*闪回\*\*: (?P<flashback>是|否)\n"
    r"- \*\*重大转折\*\*: (?P<turning>是|否)\n?",
    re.MULTILINE,
)


@dataclass(slots=True)
class TimelineEntry:
    chapter_number: int
    event_index: int
    at: str
    event: str
    is_flashback: bool
    is_major_turning_point: bool


def append_timeline_events(current_text: str, chapter_number: int, events: list[dict[str, Any]]) -> str:
    base = current_text.rstrip() if current_text.strip() else "# Timeline"
    blocks = [base, ""]
    if current_text.strip() and not current_text.endswith("\n"):
        blocks = [current_text.rstrip(), ""]
    for index, event in enumerate(events, start=1):
        blocks.extend(
            [
                f"## T{chapter_number:03d}-{index:02d}",
                f"- **时间**: {event['at']}",
                f"- **事件**: {event['event']}",
                f"- **闪回**: {'是' if event['is_flashback'] else '否'}",
                f"- **重大转折**: {'是' if event['is_major_turning_point'] else '否'}",
                "",
            ]
        )
    return "\n".join(blocks).rstrip() + "\n"


def parse_timeline_entries(text: str) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    for match in ENTRY_RE.finditer(text):
        chapter_str, event_str = match.group("id")[1:].split("-")
        entries.append(
            TimelineEntry(
                chapter_number=int(chapter_str),
                event_index=int(event_str),
                at=match.group("at"),
                event=match.group("event"),
                is_flashback=match.group("flashback") == "是",
                is_major_turning_point=match.group("turning") == "是",
            )
        )
    return entries


def last_non_flashback_time(text: str) -> str | None:
    for entry in reversed(parse_timeline_entries(text)):
        if not entry.is_flashback:
            return entry.at
    return None


def time_sort_key(value: str) -> tuple[str, int, int]:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", value):
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
        return parsed.date().isoformat(), 0, parsed.hour * 60 + parsed.minute

    date_part, period = value.rsplit(" ", 1)
    return date_part, 1, PERIOD_ORDER[period]
