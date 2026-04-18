from subprocess import run
import sys

from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response


def _seed_drafted_block(initialized_project, start_chapter: int = 1, end_chapter: int = 50) -> None:
    paths = project_paths(initialized_project)
    store = ChapterIndexStore(paths.chapter_index_file)
    for chapter_number in range(start_chapter, end_chapter + 1):
        store.upsert(
            {
                "n": chapter_number,
                "title": f"第{chapter_number:03d}章",
                "vol": 1,
                "status": "drafted",
                "summary": "",
                "updated": "2026-04-18",
            }
        )


def test_review_command_writes_notes_file(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "review", "--chapter", "2"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    notes_path = initialized_project / ".pizhi" / "chapters" / "ch002" / "notes.md"

    assert result.returncode == 0
    assert notes_path.exists()
    assert "时间线单调性" in notes_path.read_text(encoding="utf-8")


def test_review_command_full_writes_cache_report(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 6, fixture_text("ch001_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "review", "--full"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    report_path = initialized_project / ".pizhi" / "cache" / "review_full.md"

    assert result.returncode == 0
    assert report_path.exists()
    assert "Global issues:" in result.stdout


def test_review_command_full_backfills_archive_and_reports_maintenance(initialized_project, fixture_text):
    _seed_drafted_block(initialized_project)
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 50, fixture_text("ch001_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "review", "--full"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    timeline_archive = initialized_project / ".pizhi" / "archive" / "timeline_ch001-050.md"
    report_path = initialized_project / ".pizhi" / "cache" / "review_full.md"

    assert result.returncode == 0, result.stderr
    assert "Maintenance findings:" in result.stdout
    assert timeline_archive.exists()
    assert "## Maintenance" in report_path.read_text(encoding="utf-8")
    assert "Archive findings" in report_path.read_text(encoding="utf-8")
