from __future__ import annotations

from pizhi.services.review_documents import write_chapter_review_notes


def test_write_chapter_review_notes_preserves_author_notes(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## 作者备注\n\n手工备注。\n\n## A 类结构检查\n\n旧内容\n",
        encoding="utf-8",
        newline="\n",
    )

    write_chapter_review_notes(
        notes_path,
        structural_markdown="A",
        ai_review_markdown="B",
    )

    raw = notes_path.read_text(encoding="utf-8")

    assert "手工备注" in raw
    assert "## B 类 AI 审查" in raw
    assert "## A 类结构检查" in raw
    assert "A" in raw
    assert "B" in raw

