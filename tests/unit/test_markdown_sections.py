from pizhi.core.markdown_sections import split_chapter_sections


def test_split_chapter_sections_finds_required_named_blocks():
    raw = (
        "正文\n\n"
        "## characters_snapshot\n\n角色\n\n"
        "## relationships_snapshot\n\n关系\n"
    )

    sections = split_chapter_sections(raw)

    assert sections.body == "正文"
    assert sections.characters_snapshot == "角色"
    assert sections.relationships_snapshot == "关系"
