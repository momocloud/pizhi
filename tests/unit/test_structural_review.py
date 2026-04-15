from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.consistency.structural import run_structural_review


def test_structural_review_flags_non_monotonic_timeline(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    report = run_structural_review(initialized_project, chapter_number=2)

    assert report.issues
    assert report.issues[0].category == "时间线单调性"
