from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.consistency.structural import run_structural_review


def test_structural_review_flags_non_monotonic_timeline(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    report = run_structural_review(initialized_project, chapter_number=2)
    notes_path = project_paths(initialized_project).chapter_dir(2) / "notes.md"
    raw_notes = notes_path.read_text(encoding="utf-8")

    assert report.chapter_issues[2]
    assert report.chapter_issues[2][0].category == "时间线单调性"
    assert "### 问题 1" in raw_notes
    assert "- **类别**：" in raw_notes
    assert "- **严重度**：" in raw_notes
    assert "- **描述**：" in raw_notes
    assert "- **证据**：" in raw_notes
    assert "- **建议修法**：" in raw_notes


def test_structural_review_migrates_freeform_notes_without_heading(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    notes_path = project_paths(initialized_project).chapter_dir(1) / "notes.md"
    notes_path.write_text(
        "自由文本开头。\n\n第二段保留。\n\n末尾空行前一段。\n",
        encoding="utf-8",
        newline="\n",
    )

    report = run_structural_review(initialized_project, chapter_number=1)
    raw_notes = notes_path.read_text(encoding="utf-8")

    assert report.chapter_issues[1] == []
    assert "自由文本开头。" in raw_notes
    assert "第二段保留。" in raw_notes
    assert "末尾空行前一段。" in raw_notes
    assert "## 作者备注" in raw_notes
    assert "## A 类结构检查" in raw_notes
    assert "## B 类 AI 审查" in raw_notes
    assert raw_notes.count("## ") == 3


def test_structural_review_preserves_prefix_before_supported_heading(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    notes_path = project_paths(initialized_project).chapter_dir(1) / "notes.md"
    notes_path.write_text(
        "顶部自由文本。\n\n## 作者备注\n\n手工备注。\n",
        encoding="utf-8",
        newline="\n",
    )

    report = run_structural_review(initialized_project, chapter_number=1)
    raw_notes = notes_path.read_text(encoding="utf-8")

    assert report.chapter_issues[1] == []
    assert "顶部自由文本。" in raw_notes
    assert "手工备注。" in raw_notes
    assert "## 作者备注" in raw_notes
    assert "## A 类结构检查" in raw_notes
    assert "## B 类 AI 审查" in raw_notes
    assert raw_notes.count("## 作者备注") == 1
    assert raw_notes.count("## A 类结构检查") == 1
    assert raw_notes.count("## B 类 AI 审查") == 1


def test_structural_review_preserves_existing_b_section_when_unknown_heading_is_added(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    notes_path = project_paths(initialized_project).chapter_dir(1) / "notes.md"
    notes_path.write_text(
        "## 作者备注\n\n手工备注。\n\n## A 类结构检查\n\n旧 A 内容。\n\n## B 类 AI 审查\n\n旧 B 内容。\n\n## 临时标题\n\n手工补充。\n",
        encoding="utf-8",
        newline="\n",
    )

    report = run_structural_review(initialized_project, chapter_number=1)
    raw_notes = notes_path.read_text(encoding="utf-8")

    assert report.chapter_issues[1] == []
    assert "手工备注。" in raw_notes
    assert "旧 B 内容。" in raw_notes
    assert "## 临时标题" in raw_notes
    assert raw_notes.count("## 作者备注") == 1
    assert raw_notes.count("## A 类结构检查") == 1
    assert raw_notes.count("## B 类 AI 审查") == 1


def test_structural_review_migrates_freeform_notes_with_unknown_heading(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    notes_path = project_paths(initialized_project).chapter_dir(1) / "notes.md"
    notes_path.write_text(
        "自由文本开头。\n\n## 临时标题\n\n手工写的内容。\n\n尾部结尾。\n",
        encoding="utf-8",
        newline="\n",
    )

    report = run_structural_review(initialized_project, chapter_number=1)
    raw_notes = notes_path.read_text(encoding="utf-8")

    assert report.chapter_issues[1] == []
    assert "自由文本开头。" in raw_notes
    assert "## 临时标题" in raw_notes
    assert "手工写的内容。" in raw_notes
    assert "尾部结尾。" in raw_notes
    assert "## 作者备注" in raw_notes
    assert "## A 类结构检查" in raw_notes
    assert "## B 类 AI 审查" in raw_notes
    assert raw_notes.count("## 作者备注") == 1
    assert raw_notes.count("## A 类结构检查") == 1
    assert raw_notes.count("## B 类 AI 审查") == 1


def test_structural_review_tolerates_malformed_meta_json(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    paths = project_paths(initialized_project)
    meta_path = paths.chapter_dir(1) / "meta.json"
    meta_path.write_text("{not valid json", encoding="utf-8")

    report = run_structural_review(initialized_project, chapter_number=1)

    assert report.chapter_issues[1] == []


def test_structural_review_single_chapter_flags_missing_previous_chapter(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 4, fixture_text("ch001_response.md"))

    report = run_structural_review(initialized_project, chapter_number=4)

    assert any(issue.category == "章节号连续性" for issue in report.chapter_issues[4])


def test_structural_review_full_flags_overdue_foreshadowing(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 6, fixture_text("ch001_response.md"))

    report = run_structural_review(initialized_project, full=True)

    assert report.global_issues
    assert any(issue.category == "伏笔超期" for issue in report.global_issues)
