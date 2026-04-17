from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.status_report import build_status_report


def _upsert_status(initialized_project, chapter_number, status, *, title=None):
    paths = project_paths(initialized_project)
    store = ChapterIndexStore(paths.chapter_index_file)
    records = {int(record["n"]): record for record in store.read_all()}
    record = records.get(
        chapter_number,
        {
            "n": chapter_number,
            "title": title or f"Chapter {chapter_number}",
            "vol": 1,
            "status": status,
            "summary": "",
            "updated": "2026-04-17",
        },
    )
    record["status"] = status
    if title is not None:
        record["title"] = title
    store.upsert(record)


def test_build_status_report_for_initialized_project(initialized_project):
    report = build_status_report(initialized_project)

    assert report.total_planned == 260
    assert report.chapter_counts["planned"] == 0
    assert report.chapter_counts["outlined"] == 0
    assert report.latest_chapter is None
    assert report.next_chapter == 1
    assert report.pending_chapters == {"outlined": [], "drafted": [], "reviewed": []}
    assert report.active_foreshadowing_count == 0


def test_build_status_report_includes_pending_queues_and_foreshadowing(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 3, fixture_text("ch002_response.md"))
    _upsert_status(initialized_project, 2, "outlined", title="第二章 仓库平面图")
    _upsert_status(initialized_project, 3, "reviewed")

    report = build_status_report(initialized_project)

    assert [chapter.number for chapter in report.recent_chapters[:3]] == [3, 2, 1]
    assert [chapter.number for chapter in report.pending_chapters["outlined"]] == [2]
    assert [chapter.number for chapter in report.pending_chapters["drafted"]] == [1]
    assert [chapter.number for chapter in report.pending_chapters["reviewed"]] == [3]
    assert report.active_foreshadowing_count == 1
    assert [entry.entry_id for entry in report.near_payoff_foreshadowing] == ["F001"]
    assert report.overdue_foreshadowing == []


def test_build_status_report_marks_overdue_foreshadowing(initialized_project):
    paths = project_paths(initialized_project)
    _upsert_status(initialized_project, 4, "outlined", title="第四章 旧档案")
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F010 | Priority: high
- **Description**: 过期的伏笔
- **Planned Payoff**: ch002
- **Related Characters**: 沈轩

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )

    report = build_status_report(initialized_project)

    assert report.active_foreshadowing_count == 1
    assert report.near_payoff_foreshadowing == []
    assert [entry.entry_id for entry in report.overdue_foreshadowing] == ["F010"]


def test_build_status_report_marks_range_payoff_near_five_chapters_before_window(initialized_project):
    paths = project_paths(initialized_project)
    _upsert_status(initialized_project, 4, "outlined", title="第四章 前哨")
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F020 | Priority: medium
- **Description**: 区间 payoff 伏笔
- **Planned Payoff**: ch010-ch015
- **Related Characters**: 沈轩

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )

    report = build_status_report(initialized_project)

    assert [entry.entry_id for entry in report.near_payoff_foreshadowing] == ["F020"]
    assert report.overdue_foreshadowing == []


def test_build_status_report_marks_range_payoff_overdue_after_window(initialized_project):
    paths = project_paths(initialized_project)
    _upsert_status(initialized_project, 16, "outlined", title="第十六章 错过窗口")
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F021 | Priority: medium
- **Description**: 已过期的区间 payoff
- **Planned Payoff**: ch010-ch015
- **Related Characters**: 沈轩

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )

    report = build_status_report(initialized_project)

    assert report.near_payoff_foreshadowing == []
    assert [entry.entry_id for entry in report.overdue_foreshadowing] == ["F021"]


def test_build_status_report_does_not_keep_open_ended_payoff_near_forever(initialized_project):
    paths = project_paths(initialized_project)
    _upsert_status(initialized_project, 31, "outlined", title="第三十一章 余波")
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F030 | Priority: high
- **Description**: 开放式 payoff 伏笔
- **Planned Payoff**: ch030+
- **Related Characters**: 沈轩

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )

    report = build_status_report(initialized_project)

    assert report.near_payoff_foreshadowing == []
    assert report.overdue_foreshadowing == []
