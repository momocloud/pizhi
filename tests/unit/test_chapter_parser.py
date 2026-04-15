from pathlib import Path

from pizhi.services.chapter_parser import parse_chapter_response


def test_parse_chapter_response_fixture():
    raw = Path("tests/fixtures/chapter_outputs/ch001_response.md").read_text(encoding="utf-8")

    parsed = parse_chapter_response(raw)

    assert parsed.metadata.chapter_title == "第一章 雨夜访客"
    assert parsed.metadata.worldview_changed is True
    assert parsed.sections.worldview_patch is not None
    assert "沈轩" in parsed.sections.characters_snapshot
