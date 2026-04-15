from pizhi.core.frontmatter import parse_frontmatter


def test_parse_frontmatter_returns_metadata_and_body():
    raw = "---\nchapter_title: Test\n---\nBody\n"

    metadata, body = parse_frontmatter(raw)

    assert metadata["chapter_title"] == "Test"
    assert body == "Body\n"
