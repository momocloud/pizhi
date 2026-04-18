from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.archive_service import rotate_archives


def _seed_latest_chapter(paths, chapter_number: int) -> None:
    ChapterIndexStore(paths.chapter_index_file).upsert(
        {
            "n": chapter_number,
            "title": f"第{chapter_number:03d}章",
            "vol": 1,
            "status": "drafted",
            "summary": "",
            "updated": "2026-04-18",
        }
    )


def test_archive_service_rotates_sealed_timeline_range(initialized_project):
    paths = project_paths(initialized_project)
    _seed_latest_chapter(paths, 50)
    paths.timeline_file.write_text(
        """# Timeline

## T001-01
- **时间**: 1986-03-14 夜
- **事件**: 沈轩抵达码头三号仓
- **闪回**: 否
- **重大转折**: 否

## T051-01
- **时间**: 1986-05-01 夜
- **事件**: 被掩盖的证词重现
- **闪回**: 否
- **重大转折**: 是
""",
        encoding="utf-8",
    )

    first_result = rotate_archives(initialized_project)
    second_result = rotate_archives(initialized_project)

    archive_text = (paths.archive_dir / "timeline_ch001-050.md").read_text(encoding="utf-8")
    timeline_text = paths.timeline_file.read_text(encoding="utf-8")

    assert first_result.findings == []
    assert second_result.findings == []
    assert archive_text.startswith("# Timeline Archive: ch001-ch050")
    assert "## T001-01" in archive_text
    assert "## T001-01" not in timeline_text
    assert "## T051-01" in timeline_text


def test_archive_service_treats_existing_matching_timeline_archive_as_noop(initialized_project):
    paths = project_paths(initialized_project)
    _seed_latest_chapter(paths, 50)
    paths.archive_dir.mkdir(parents=True, exist_ok=True)
    expected_archive = """# Timeline Archive: ch001-ch050

## T001-01
- **时间**: 1986-03-14 夜
- **事件**: 沈轩抵达码头三号仓
- **闪回**: 否
- **重大转折**: 否
"""
    (paths.archive_dir / "timeline_ch001-050.md").write_text(expected_archive, encoding="utf-8")
    paths.timeline_file.write_text(
        """# Timeline

## T001-01
- **时间**: 1986-03-14 夜
- **事件**: 沈轩抵达码头三号仓
- **闪回**: 否
- **重大转折**: 否

## T051-01
- **时间**: 1986-05-01 夜
- **事件**: 被掩盖的证词重现
- **闪回**: 否
- **重大转折**: 是
""",
        encoding="utf-8",
    )

    result = rotate_archives(initialized_project)

    assert result.findings == []
    assert (paths.archive_dir / "timeline_ch001-050.md").read_text(encoding="utf-8") == expected_archive
    assert "## T001-01" not in paths.timeline_file.read_text(encoding="utf-8")
    assert "## T051-01" in paths.timeline_file.read_text(encoding="utf-8")


def test_archive_service_reports_conflicting_existing_foreshadowing_archive(initialized_project):
    paths = project_paths(initialized_project)
    _seed_latest_chapter(paths, 50)
    paths.archive_dir.mkdir(parents=True, exist_ok=True)
    conflicting_archive = """# Foreshadowing Archive: ch001-ch050

## Resolved
### F010
- **Resolution**: wrong content

## Abandoned
"""
    archive_path = paths.archive_dir / "foreshadowing_ch001-050.md"
    archive_path.write_text(conflicting_archive, encoding="utf-8")
    live_text = """# Foreshadowing Tracker

## Active

## Referenced

## Resolved
### F010 | Priority: high
- **Description**: 正常关闭的伏笔
- **Resolution**: 真相揭露
- **Resolved In**: ch012

## Abandoned
"""
    paths.foreshadowing_file.write_text(live_text, encoding="utf-8")

    result = rotate_archives(initialized_project)

    assert archive_path.read_text(encoding="utf-8") == conflicting_archive
    assert "F010" in paths.foreshadowing_file.read_text(encoding="utf-8")
    assert result.findings
    assert result.findings[0].artifact == "foreshadowing"
    assert "conflict" in result.findings[0].description


def test_archive_service_keeps_closed_foreshadowing_without_close_chapter_live(initialized_project):
    paths = project_paths(initialized_project)
    _seed_latest_chapter(paths, 50)
    paths.archive_dir.mkdir(parents=True, exist_ok=True)
    (paths.archive_dir / "timeline_ch001-050.md").write_text(
        """# Timeline Archive: ch001-ch050

## T001-01
- **时间**: 1986-03-14 夜
- **事件**: 沈轩抵达码头三号仓
- **闪回**: 否
- **重大转折**: 否
""",
        encoding="utf-8",
    )
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active

## Referenced

## Resolved
### F010 | Priority: high
- **Description**: 正常关闭的伏笔
- **Resolution**: 真相揭露
- **Resolved In**: ch012

### F099 | Priority: low
- **Description**: missing close chapter
- **Resolution**: 尚未写明关闭章节

## Abandoned
""",
        encoding="utf-8",
    )

    result = rotate_archives(initialized_project)

    assert (paths.archive_dir / "foreshadowing_ch001-050.md").exists()
    assert "F010" in (paths.archive_dir / "foreshadowing_ch001-050.md").read_text(encoding="utf-8")
    assert "F099" in paths.foreshadowing_file.read_text(encoding="utf-8")
    assert result.findings
    assert "missing close chapter" in result.findings[0].description


def test_archive_service_archives_resolved_and_abandoned_foreshadowing_without_dropping_live_content(initialized_project):
    paths = project_paths(initialized_project)
    _seed_latest_chapter(paths, 50)
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 活动伏笔
- **Planned Payoff**: ch055
- **Related Characters**: 沈轩

## Referenced
### F002
- **Referenced**: true

### BROKEN
- **Description**: malformed block that must stay live

## Resolved
### F010 | Priority: high
- **Description**: 已完成伏笔
- **Resolution**: 真相揭露
- **Resolved In**: ch012

## Abandoned
### F020 | Priority: low
- **Description**: 已放弃伏笔
- **Abandoned In**: ch045
- **Related Characters**: 阿坤
""",
        encoding="utf-8",
    )

    result = rotate_archives(initialized_project)

    archive_text = (paths.archive_dir / "foreshadowing_ch001-050.md").read_text(encoding="utf-8")
    live_text = paths.foreshadowing_file.read_text(encoding="utf-8")

    assert result.findings == []
    assert "### F010" in archive_text
    assert "### F020" in archive_text
    assert "### F001" not in archive_text
    assert "### F002" not in archive_text
    assert "### F001 | Priority: high" in live_text
    assert "### F002" in live_text
    assert "### BROKEN" in live_text
    assert "### F010" not in live_text
    assert "### F020" not in live_text


def test_archive_service_keeps_archiving_other_artifact_when_one_conflicts(initialized_project):
    paths = project_paths(initialized_project)
    _seed_latest_chapter(paths, 50)
    paths.archive_dir.mkdir(parents=True, exist_ok=True)
    (paths.archive_dir / "timeline_ch001-050.md").write_text(
        """# Timeline Archive: ch001-ch050

## T001-01
- **时间**: 1986-03-14 夜
- **事件**: already archived but conflicting
- **闪回**: 否
- **重大转折**: 否
""",
        encoding="utf-8",
    )
    paths.timeline_file.write_text(
        """# Timeline

## T001-01
- **时间**: 1986-03-14 夜
- **事件**: 沈轩抵达码头三号仓
- **闪回**: 否
- **重大转折**: 否

## T051-01
- **时间**: 1986-05-01 夜
- **事件**: 被掩盖的证词重现
- **闪回**: 否
- **重大转折**: 是
""",
        encoding="utf-8",
    )
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active

## Referenced

## Resolved
### F010 | Priority: high
- **Description**: 已完成伏笔
- **Resolution**: 真相揭露
- **Resolved In**: ch012

## Abandoned
""",
        encoding="utf-8",
    )

    result = rotate_archives(initialized_project)

    assert any(finding.artifact == "timeline" for finding in result.findings)
    assert (paths.archive_dir / "timeline_ch001-050.md").read_text(encoding="utf-8").startswith(
        "# Timeline Archive: ch001-ch050"
    )
    assert (paths.archive_dir / "foreshadowing_ch001-050.md").exists()
    assert "F010" not in paths.foreshadowing_file.read_text(encoding="utf-8")
    assert "## T001-01" in paths.timeline_file.read_text(encoding="utf-8")
