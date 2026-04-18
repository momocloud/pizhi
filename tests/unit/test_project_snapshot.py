from pizhi.domain.project_state import ArchiveRange
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.project_snapshot import load_project_snapshot


def test_load_project_snapshot_for_initialized_project(initialized_project):
    snapshot = load_project_snapshot(initialized_project)

    assert snapshot.project_name == "Test Novel"
    assert snapshot.latest_chapter is None
    assert snapshot.next_chapter == 1
    assert snapshot.chapters == {}


def test_load_project_snapshot_tracks_chapter_artifacts(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    snapshot = load_project_snapshot(initialized_project)

    assert snapshot.latest_chapter == 1
    assert snapshot.chapters[1].artifacts.text_exists is True
    assert snapshot.chapters[1].artifacts.meta_exists is True


def test_load_project_snapshot_tolerates_malformed_meta_json(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    meta_path = initialized_project / ".pizhi" / "chapters" / "ch001" / "meta.json"
    meta_path.write_text("{not valid json", encoding="utf-8")

    snapshot = load_project_snapshot(initialized_project)

    assert snapshot.latest_chapter == 1
    assert snapshot.chapters[1].artifacts.meta_exists is True
    assert snapshot.chapters[1].metadata == {}


def test_load_project_snapshot_includes_foreshadowing_entries(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    snapshot = load_project_snapshot(initialized_project)

    assert len(snapshot.foreshadowing_entries) == 1
    assert snapshot.foreshadowing_entries[0].entry_id == "F001"
    assert snapshot.foreshadowing_entries[0].section == "Active"
    assert snapshot.foreshadowing_entries[0].planned_payoff.start_chapter == 5
    assert snapshot.foreshadowing_entries[0].planned_payoff.end_chapter == 5


def test_load_project_snapshot_discovers_existing_archive_ranges(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    archive_dir = initialized_project / ".pizhi" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "timeline_ch001-050.md").write_text(
        """# Timeline Archive: ch001-ch050

## T001-01
- **时间**: 1986-03-14 夜
- **事件**: 沈轩抵达码头三号仓
- **闪回**: 否
- **重大转折**: 否
""",
        encoding="utf-8",
    )

    snapshot = load_project_snapshot(initialized_project)

    assert snapshot.existing_timeline_archive_ranges == [ArchiveRange(1, 50)]
    assert snapshot.existing_foreshadowing_archive_ranges == []
    assert [entry.entry_id for entry in snapshot.active_or_referenced_foreshadowing] == ["F001"]


def test_load_project_snapshot_includes_archived_major_turning_points(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    (initialized_project / ".pizhi" / "global" / "timeline.md").write_text(
        """# Timeline

## T001-01
- **时间**: 1986-03-14 夜
- **事件**: 沈轩抵达码头三号仓
- **闪回**: 否
- **重大转折**: 是
""",
        encoding="utf-8",
    )

    archive_dir = initialized_project / ".pizhi" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "timeline_ch051-100.md").write_text(
        """# Timeline Archive: ch051-ch100

## T060-02
- **时间**: 1986-05-01 夜
- **事件**: 被掩盖的证词重现
- **闪回**: 否
- **重大转折**: 是
""",
        encoding="utf-8",
    )

    snapshot = load_project_snapshot(initialized_project)

    assert [entry.event_id for entry in snapshot.major_turning_points] == ["T001-01", "T060-02"]


def test_load_project_snapshot_handles_missing_foreshadowing_file(initialized_project):
    foreshadowing_file = initialized_project / ".pizhi" / "global" / "foreshadowing.md"
    foreshadowing_file.unlink()

    snapshot = load_project_snapshot(initialized_project)

    assert snapshot.foreshadowing_entries == []


def test_load_project_snapshot_skips_invalid_foreshadowing_entries(initialized_project):
    foreshadowing_file = initialized_project / ".pizhi" / "global" / "foreshadowing.md"
    foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 合法伏笔
- **Planned Payoff**: ch018
- **Related Characters**: 沈轩

### F002 | Priority: medium
- **Description**: 坏掉的伏笔
- **Planned Payoff**: ????
- **Related Characters**: 阿坤

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )

    snapshot = load_project_snapshot(initialized_project)

    assert [entry.entry_id for entry in snapshot.foreshadowing_entries] == ["F001"]


def test_load_project_snapshot_skips_invalid_header_block_and_keeps_valid_entries(initialized_project):
    foreshadowing_file = initialized_project / ".pizhi" / "global" / "foreshadowing.md"
    foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 合法伏笔一
- **Planned Payoff**: ch005
- **Related Characters**: 沈轩

### BROKEN
- **Description**: 坏掉的头部
- **Planned Payoff**: ch999

### F003 | Priority: low
- **Description**: 合法伏笔二
- **Planned Payoff**: ch018
- **Related Characters**: 阿坤

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )

    snapshot = load_project_snapshot(initialized_project)

    assert [entry.entry_id for entry in snapshot.foreshadowing_entries] == ["F001", "F003"]
    assert snapshot.foreshadowing_entries[0].description == "合法伏笔一"
    assert snapshot.foreshadowing_entries[0].planned_payoff.start_chapter == 5
    assert snapshot.foreshadowing_entries[1].description == "合法伏笔二"
