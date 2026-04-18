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


def test_split_chapter_sections_keeps_nested_coverage_markers_inside_synopsis_new():
    raw = (
        "正文\n\n"
        "## characters_snapshot\n\n角色\n\n"
        "## relationships_snapshot\n\n关系\n\n"
        "## synopsis_new\n\n"
        "# Synopsis\n\n"
        "概要正文。\n\n"
        "## coverage_markers\n"
        "foreshadowing_ids:\n"
        "- F001\n"
        "major_turning_points:\n"
        "- T001-02\n"
    )

    sections = split_chapter_sections(raw)

    assert "# Synopsis" in sections.synopsis_new
    assert "## coverage_markers" in sections.synopsis_new
    assert "foreshadowing_ids:" in sections.synopsis_new
