from pizhi.services.outline_service import parse_outline_response


def test_parse_outline_response_returns_chapter_blocks(project_root):
    response_text = (
        project_root / "tests" / "fixtures" / "orchestration" / "outline_expand_response.md"
    ).read_text(encoding="utf-8")

    parsed = parse_outline_response(response_text)

    assert parsed[0].chapter_number == 1
    assert parsed[0].title == "雨夜访客"
    assert "第一起命案" in parsed[0].body
