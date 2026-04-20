from __future__ import annotations

from pizhi.services.agent_extensions import ExtensionReportSection
from pizhi.services.agent_extensions import render_extension_runtime_failure_section
from pizhi.services.agent_extensions import render_extension_setup_failure_section
from pizhi.services.review_documents import load_chapter_review_notes
from pizhi.services.review_documents import write_full_review_document
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

    assert loaded.author_notes == ""
    assert loaded.ai_review_markdown == ""


def test_load_chapter_review_notes_preserves_existing_machine_sections_with_unknown_heading(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## 作者备注\n\n手工备注。\n\n## A 类结构检查\n\n旧 A 内容。\n\n## B 类 AI 审查\n\n旧 B 内容。\n\n## 临时标题\n\n手工补充。\n",
        encoding="utf-8",
        newline="\n",
    )

    loaded = load_chapter_review_notes(notes_path)

    assert "手工备注。" in loaded.author_notes
    assert "## 临时标题" in loaded.author_notes
    assert "手工补充。" in loaded.author_notes
    assert loaded.ai_review_markdown == "\n旧 B 内容。\n\n"


def test_load_chapter_review_notes_preserves_prefix_before_supported_heading(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "顶部自由文本。\n\n## 作者备注\n\n手工备注。\n",
        encoding="utf-8",
        newline="\n",
    )

    loaded = load_chapter_review_notes(notes_path)

    assert loaded.author_notes == "顶部自由文本。\n\n\n手工备注。\n"
    assert loaded.ai_review_markdown == ""


def test_load_chapter_review_notes_preserves_duplicate_author_heading_text(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## 作者备注\n\n第一段手工备注。\n\n## 作者备注\n\n第二段手工备注。\n\n## A 类结构检查\n\n旧 A 内容。\n\n## B 类 AI 审查\n\n旧 B 内容。\n",
        encoding="utf-8",
        newline="\n",
    )

    loaded = load_chapter_review_notes(notes_path)
    write_chapter_review_notes(
        notes_path,
        author_notes=loaded.author_notes,
        structural_markdown="新 A 内容。\n",
        ai_review_markdown="新 B 内容。\n",
    )

    raw = notes_path.read_text(encoding="utf-8")

    assert "第一段手工备注。" in raw
    assert "第二段手工备注。" in raw
    assert raw.count("## 作者备注") == 1
    assert raw.count("## A 类结构检查") == 1
    assert raw.count("## B 类 AI 审查") == 1


def test_load_chapter_review_notes_recovers_duplicate_machine_headings_when_rewriting(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## 作者备注\n\n手工备注。\n\n## A 类结构检查\n\n旧 A 内容 1。\n\n## B 类 AI 审查\n\n旧 B 内容 1。\n\n## A 类结构检查\n\n旧 A 内容 2。\n\n## B 类 AI 审查\n\n旧 B 内容 2。\n\n## 临时标题\n\n手工补充。\n",
        encoding="utf-8",
        newline="\n",
    )

    loaded = load_chapter_review_notes(notes_path)
    write_chapter_review_notes(
        notes_path,
        author_notes=loaded.author_notes,
        structural_markdown="新 A 内容。\n",
        ai_review_markdown=loaded.ai_review_markdown,
    )

    raw = notes_path.read_text(encoding="utf-8")

    assert "手工备注。" in raw
    assert "## 临时标题" in raw
    assert "旧 A 内容 1。" not in raw
    assert "旧 B 内容 1。" not in raw
    assert "旧 A 内容 2。" in raw
    assert "旧 B 内容 2。" in raw
    assert raw.count("## A 类结构检查") == 2
    assert raw.count("## B 类 AI 审查") == 2
    assert raw.count("## ") == 6


def test_load_chapter_review_notes_recovers_duplicate_machine_sections_into_author_notes(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## 作者备注\n\n手工备注。\n\n## A 类结构检查\n\n旧 A 内容 1。\n\n## 一致性检查结果\n\n旧 C 内容 1。\n\n## B 类 AI 审查\n\n旧 B 内容 1。\n\n## A 类结构检查\n\n旧 A 内容 2。\n\n## 一致性检查结果\n\n旧 C 内容 2。\n\n## B 类 AI 审查\n\n旧 B 内容 2。\n",
        encoding="utf-8",
        newline="\n",
    )

    loaded = load_chapter_review_notes(notes_path)
    write_chapter_review_notes(
        notes_path,
        author_notes=loaded.author_notes,
        structural_markdown="新 A 内容。\n",
        ai_review_markdown="新 B 内容。\n",
    )

    raw = notes_path.read_text(encoding="utf-8")

    assert "手工备注。" in raw
    assert "旧 A 内容 2。" in raw
    assert "旧 B 内容 2。" in raw
    assert "旧 C 内容 2。" in raw
    assert "旧 A 内容 1。" not in raw
    assert "旧 B 内容 1。" not in raw
    assert "旧 C 内容 1。" not in raw
    assert raw.count("## A 类结构检查") == 2
    assert raw.count("## B 类 AI 审查") == 2
    assert raw.count("## 一致性检查结果") == 1


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


def test_write_chapter_review_notes_appends_extension_sections(tmp_path):
    notes_path = tmp_path / "notes.md"

    write_chapter_review_notes(
        notes_path,
        author_notes="author",
        structural_markdown="- structural\n",
        ai_review_markdown="- ai\n",
        extension_sections=[
            ExtensionReportSection(
                agent_id="critique.chapter",
                title="Review Agent critique.chapter",
                body="- issue\n",
            ),
        ],
    )

    raw = notes_path.read_text(encoding="utf-8")

    assert "## 作者备注" in raw
    assert "## Review Agent critique.chapter" in raw
    assert "- issue" in raw


def test_render_extension_failure_sections_quote_markdown_headings():
    setup_section = render_extension_setup_failure_section("trace\n## setup heading\nmore")
    runtime_section = render_extension_runtime_failure_section(
        "critique.chapter",
        "trace\n## runtime heading\nmore",
    )

    assert setup_section.body.startswith("- Status: failed\n- Error: extension setup/load failure\n\n> trace\n> ## setup heading\n> more\n")
    assert runtime_section.body.startswith("- Status: failed\n- Error: extension runtime failure\n\n> trace\n> ## runtime heading\n> more\n")
    assert all(
        not line.startswith("## ")
        for line in setup_section.body.splitlines()
    )
    assert all(
        not line.startswith("## ")
        for line in runtime_section.body.splitlines()
    )


def test_load_and_write_chapter_review_notes_keep_failure_text_out_of_section_boundaries(tmp_path):
    notes_path = tmp_path / "notes.md"
    failure_section = render_extension_runtime_failure_section(
        "critique.chapter",
        "runtime failed\n## nested heading\nstill details",
    )

    write_chapter_review_notes(
        notes_path,
        author_notes="作者备注。\n",
        structural_markdown="结构检查。\n",
        ai_review_markdown="AI 审查。\n",
        extension_sections=[failure_section],
    )

    loaded = load_chapter_review_notes(notes_path)
    assert loaded.author_notes.strip() == "作者备注。"
    assert loaded.ai_review_markdown.strip() == "AI 审查。"
    assert "nested heading" not in loaded.author_notes
    assert "nested heading" not in loaded.ai_review_markdown

    write_chapter_review_notes(
        notes_path,
        author_notes=loaded.author_notes,
        structural_markdown="重写结构检查。\n",
        ai_review_markdown=loaded.ai_review_markdown,
        extension_sections=[failure_section],
    )

    raw = notes_path.read_text(encoding="utf-8")
    top_level_headings = [line for line in raw.splitlines() if line.startswith("## ")]
    assert top_level_headings == [
        "## 作者备注",
        "## A 类结构检查",
        "## B 类 AI 审查",
        "## Review Agent critique.chapter",
    ]
    assert "## nested heading" not in top_level_headings
    assert "runtime failed" in raw


def test_load_chapter_review_notes_treats_extension_only_sections_as_machine_managed(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## Review Agent critique.chapter\n\n- issue\n",
        encoding="utf-8",
        newline="\n",
    )

    loaded = load_chapter_review_notes(notes_path)
    write_chapter_review_notes(
        notes_path,
        author_notes=loaded.author_notes,
        structural_markdown="A\n",
        ai_review_markdown="B\n",
    )

    raw = notes_path.read_text(encoding="utf-8")

    assert loaded.author_notes == ""
    assert loaded.ai_review_markdown == ""
    assert "## 作者备注" in raw
    assert "## Review Agent critique.chapter" not in raw
    assert raw.count("## ") == 3


def test_write_full_review_document_writes_fixed_sections_in_order(tmp_path):
    report_path = tmp_path / "review_full.md"

    write_full_review_document(
        report_path,
        summary_markdown="- Summary line.\n",
        structural_markdown="- Structural line.\n",
        maintenance_markdown="- Maintenance line.\n",
        ai_review_markdown="### 问题 1\n- **类别**：人物一致性\n- **严重度**：高\n- **描述**：补充动机铺垫。\n- **证据**：示例证据。\n- **建议修法**：补写心理铺垫。\n",
    )

    raw = report_path.read_text(encoding="utf-8")

    assert raw.startswith("# Review Full\n\n## Summary\n\n")
    assert raw.index("## Summary") < raw.index("## A 类结构检查") < raw.index("## Maintenance") < raw.index("## B 类 AI 审查")
    assert "- Summary line." in raw
    assert "- Structural line." in raw
    assert "- Maintenance line." in raw
    assert "人物一致性" in raw
    assert "补充动机铺垫" in raw
    assert "补写心理铺垫。" in raw
