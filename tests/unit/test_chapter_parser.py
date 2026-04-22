from pathlib import Path

import pytest

from pizhi.services.chapter_parser import parse_chapter_response


def test_parse_chapter_response_fixture():
    raw = Path(__file__).resolve().parents[1] / "fixtures" / "chapter_outputs" / "ch001_response.md"
    raw = raw.read_text(encoding="utf-8")

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


def test_parse_chapter_response_rejects_malformed_foreshadowing_introduced_item():
    raw = """---
chapter_title: "第一章 雨夜访客"
word_count_estimated: 3200
characters_involved:
  - 沈轩
  - 阿坤
worldview_changed: false
synopsis_changed: false
timeline_events: []
foreshadowing:
  introduced:
    - F001
  referenced: []
  resolved: []
---

## characters_snapshot

# 第一章角色状态

## relationships_snapshot

# 第一章人物关系

## worldview_patch

# 第一章世界观变更
"""

    with pytest.raises(ValueError, match="foreshadowing"):
        parse_chapter_response(raw)
