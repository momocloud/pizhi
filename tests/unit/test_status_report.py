from pizhi.services.status_report import build_status_report


def test_build_status_report_for_initialized_project(initialized_project):
    report = build_status_report(initialized_project)

    assert report.total_planned == 260
    assert report.chapter_counts["planned"] == 0
    assert report.chapter_counts["outlined"] == 0
    assert report.latest_chapter is None
    assert report.next_chapter == 1
