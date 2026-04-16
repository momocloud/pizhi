from pizhi.services.chapter_context import build_chapter_context
from pizhi.services.chapter_writer import apply_chapter_response


def test_build_chapter_context_includes_previous_chapter_artifacts(initialized_project, fixture_text):
    apply_chapter_response(
        initialized_project,
        chapter_number=1,
        raw_response=fixture_text("ch001_response.md"),
    )
    chapter_two_dir = initialized_project / ".pizhi" / "chapters" / "ch002"
    chapter_two_dir.mkdir(parents=True, exist_ok=True)
    (chapter_two_dir / "outline.md").write_text(
        "# 第002章 码头血衣\n\n- 沈轩带着血衣离开码头。\n",
        encoding="utf-8",
    )

    context = build_chapter_context(initialized_project, chapter_number=2)

    assert "synopsis" in context.required_inputs
    assert "previous_text" in context.required_inputs
    assert "current_outline" in context.required_inputs
    assert "码头血衣" in context.required_inputs["current_outline"]
