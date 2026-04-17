from subprocess import run
import sys

from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response


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


def test_status_command_prints_summary(initialized_project):
    result = run(
        [sys.executable, "-m", "pizhi", "status"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Total planned chapters: 260" in result.stdout
    assert "Next chapter: ch001" in result.stdout
    assert "Recent chapters:" in result.stdout
    assert "Pending chapters:" in result.stdout
    assert "Foreshadowing:" in result.stdout


def test_status_command_prints_dashboard_sections(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    _upsert_status(initialized_project, 2, "outlined", title="第二章 仓库平面图")

    result = run(
        [sys.executable, "-m", "pizhi", "status"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Recent chapters:" in result.stdout
    assert "Pending chapters:" in result.stdout
    assert "Foreshadowing:" in result.stdout
    assert "ch001" in result.stdout
    assert "F001" in result.stdout
