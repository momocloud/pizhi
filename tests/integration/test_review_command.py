from subprocess import run
import sys

from pizhi.services.chapter_writer import apply_chapter_response


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
