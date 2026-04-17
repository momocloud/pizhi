from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.consistency.structural import run_structural_review


def test_structural_review_flags_non_monotonic_timeline(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    report = run_structural_review(initialized_project, chapter_number=2)

    assert report.chapter_issues[2]
    assert report.chapter_issues[2][0].category == "时间线单调性"


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
