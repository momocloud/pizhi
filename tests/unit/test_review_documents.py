from __future__ import annotations

from pizhi.services.review_documents import load_chapter_review_notes
from pizhi.services.review_documents import write_chapter_review_notes


def test_load_chapter_review_notes_treats_freeform_notes_as_author_notes(tmp_path):
    notes_path = tmp_path / "notes.md"
    raw_notes = "前导空行\n\n作者第一段。\n\n作者第二段。\n\n尾部空行\n"
    notes_path.write_text(raw_notes, encoding="utf-8", newline="\n")

    loaded = load_chapter_review_notes(notes_path)

    assert loaded.author_notes == raw_notes
    assert loaded.ai_review_markdown == ""


def test_load_chapter_review_notes_treats_unknown_heading_as_freeform_notes(tmp_path):
    notes_path = tmp_path / "notes.md"
    raw_notes = "自由文本开头。\n\n## 临时标题\n\n手工写的内容。\n\n尾部结尾。\n"
    notes_path.write_text(raw_notes, encoding="utf-8", newline="\n")

    loaded = load_chapter_review_notes(notes_path)

    assert loaded.author_notes == raw_notes
    assert loaded.ai_review_markdown == ""


def test_load_chapter_review_notes_accepts_legacy_consistency_section(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## 一致性检查结果\n\n旧 deterministic 内容。\n",
        encoding="utf-8",
        newline="\n",
    )

    loaded = load_chapter_review_notes(notes_path)

    assert loaded.author_notes == "\n旧 deterministic 内容。\n"
    assert loaded.ai_review_markdown == ""


def test_write_chapter_review_notes_preserves_author_notes_and_drops_legacy_sections(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## 作者备注\n\n手工备注。\n\n第二段。\n\n## 一致性检查结果\n\n旧内容\n",
        encoding="utf-8",
        newline="\n",
    )

    loaded = load_chapter_review_notes(notes_path)
    write_chapter_review_notes(
        notes_path,
        author_notes=loaded.author_notes,
        structural_markdown="A",
        ai_review_markdown="B",
    )

    raw = notes_path.read_text(encoding="utf-8")

    assert "手工备注" in raw
    assert "第二段" in raw
    assert "## 一致性检查结果" not in raw
    assert raw.count("## 作者备注") == 1
    assert raw.count("## A 类结构检查") == 1
    assert raw.count("## B 类 AI 审查") == 1
    assert raw.count("## ") == 3
    assert "## B 类 AI 审查" in raw
    assert "A" in raw
    assert "B" in raw
    assert raw.index("手工备注。") < raw.index("第二段。")
