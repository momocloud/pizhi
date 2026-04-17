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


def test_load_project_snapshot_includes_foreshadowing_entries(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    snapshot = load_project_snapshot(initialized_project)

    assert len(snapshot.foreshadowing_entries) == 1
    assert snapshot.foreshadowing_entries[0].entry_id == "F001"
    assert snapshot.foreshadowing_entries[0].section == "Active"
    assert snapshot.foreshadowing_entries[0].planned_payoff.start_chapter == 5
    assert snapshot.foreshadowing_entries[0].planned_payoff.end_chapter == 5


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
