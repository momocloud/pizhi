from pizhi.services.chapter_writer import apply_chapter_response


def test_apply_chapter_response_writes_chapter_and_updates_index(initialized_project, fixture_text):
    result = apply_chapter_response(
        initialized_project,
        chapter_number=1,
        raw_response=fixture_text("ch001_response.md"),
    )

    assert result.chapter_dir.joinpath("text.md").exists()
    assert result.chapter_dir.joinpath("characters.md").exists()
    assert result.chapter_dir.joinpath("relationships.md").exists()
    assert result.chapter_dir.joinpath("worldview_patch.md").exists()

    index_text = initialized_project.joinpath(".pizhi", "chapters", "index.jsonl").read_text(encoding="utf-8")
    timeline_text = initialized_project.joinpath(".pizhi", "global", "timeline.md").read_text(encoding="utf-8")
    foreshadowing_text = initialized_project.joinpath(".pizhi", "global", "foreshadowing.md").read_text(encoding="utf-8")

    assert '"status": "drafted"' in index_text
    assert "第一章 雨夜访客" in index_text
    assert "T001-01" in timeline_text
    assert "F001" in foreshadowing_text
