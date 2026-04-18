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
