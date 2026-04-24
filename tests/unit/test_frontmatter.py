from pizhi.core.frontmatter import parse_frontmatter


def test_parse_frontmatter_returns_metadata_and_body():
    raw = "---\nchapter_title: Test\n---\nBody\n"

    metadata, body = parse_frontmatter(raw)

    assert metadata["chapter_title"] == "Test"
    assert body == "Body\n"


def test_parse_frontmatter_repairs_backslash_escaped_apostrophe_in_single_quoted_scalar():
    raw = (
        "---\n"
        "foreshadowing:\n"
        "  introduced:\n"
        "    - id: F003\n"
        "      planned_payoff: 'Revelation of the fae\\'s hidden agenda'\n"
        "---\n"
        "Body\n"
    )

    metadata, body = parse_frontmatter(raw)

    assert metadata["foreshadowing"]["introduced"][0]["planned_payoff"] == "Revelation of the fae's hidden agenda"
    assert body == "Body\n"


def test_parse_frontmatter_repairs_plain_apostrophe_inside_single_quoted_scalar():
    raw = (
        "---\n"
        "foreshadowing:\n"
        "  introduced:\n"
        "    - id: F006\n"
        "      planned_payoff: 'The caller will be revealed as Mei's uncle in chapter 8'\n"
        "---\n"
        "Body\n"
    )

    metadata, body = parse_frontmatter(raw)

    assert (
        metadata["foreshadowing"]["introduced"][0]["planned_payoff"]
        == "The caller will be revealed as Mei's uncle in chapter 8"
    )
    assert body == "Body\n"


def test_parse_frontmatter_repairs_key_value_quoted_prefix_followed_by_text():
    raw = (
        "---\n"
        "foreshadowing:\n"
        "  introduced:\n"
        "    - id: F004\n"
        "      desc: \"帷幕维护局\"的存在及其对觉醒者的强制登记制度\n"
        "---\n"
        "Body\n"
    )

    metadata, body = parse_frontmatter(raw)

    assert metadata["foreshadowing"]["introduced"][0]["desc"] == "\"帷幕维护局\"的存在及其对觉醒者的强制登记制度"
    assert body == "Body\n"
