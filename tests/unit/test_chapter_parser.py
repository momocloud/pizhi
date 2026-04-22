from pathlib import Path

import pytest

from pizhi.services.chapter_parser import parse_chapter_response


def test_parse_chapter_response_fixture():
    raw = Path("tests/fixtures/chapter_outputs/ch001_response.md").read_text(encoding="utf-8")

    parsed = parse_chapter_response(raw)

    assert parsed.metadata.chapter_title == "第一章 雨夜访客"
    assert parsed.metadata.worldview_changed is True
    assert parsed.sections.worldview_patch is not None
    assert "沈轩" in parsed.sections.characters_snapshot


def test_parse_chapter_response_rejects_parseable_but_invalid_nested_timeline_event():
    raw = """---
chapter_title: 第七章
word_count_estimated: 1200
characters_involved: []
worldview_changed: false
synopsis_changed: false
timeline_events:
  - event: 没有时间字段的事件
    is_flashback: false
    is_major_turning_point: false
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---
正文

---

## characters_snapshot

角色

## relationships_snapshot

关系
"""

    with pytest.raises(ValueError, match=r"timeline_events\[0\].*at"):
        parse_chapter_response(raw)
