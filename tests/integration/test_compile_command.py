import sys
from subprocess import run

from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response


def _chapter_statuses(initialized_project) -> dict[int, str]:
    paths = project_paths(initialized_project)
    store = ChapterIndexStore(paths.chapter_index_file)
    return {int(record["n"]): record["status"] for record in store.read_all()}


def test_compile_command_writes_volume_file(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    apply_chapter_response(initialized_project, 21, fixture_text("ch001_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "compile", "--volume", "1"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (initialized_project / "manuscript" / "vol_01.md").exists()
    assert _chapter_statuses(initialized_project)[1] == "compiled"
    assert _chapter_statuses(initialized_project)[2] == "compiled"
    assert _chapter_statuses(initialized_project)[21] == "drafted"


def test_compile_command_writes_chapter_file(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "compile", "--chapter", "2"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (initialized_project / "manuscript" / "ch002.md").exists()
    assert _chapter_statuses(initialized_project)[1] == "drafted"
    assert _chapter_statuses(initialized_project)[2] == "compiled"


def test_compile_command_writes_chapter_range_file(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    apply_chapter_response(initialized_project, 3, fixture_text("ch001_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "compile", "--chapters", "2-3"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (initialized_project / "manuscript" / "ch002-ch003.md").exists()
    assert _chapter_statuses(initialized_project)[1] == "drafted"
    assert _chapter_statuses(initialized_project)[2] == "compiled"
    assert _chapter_statuses(initialized_project)[3] == "compiled"


def test_compile_command_rejects_missing_text_without_partial_success(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    (initialized_project / ".pizhi" / "chapters" / "ch002" / "text.md").unlink()

    result = run(
        [sys.executable, "-m", "pizhi", "compile", "--chapters", "1-2"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "text.md" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (initialized_project / "manuscript" / "ch001-ch002.md").exists()
    assert _chapter_statuses(initialized_project)[1] == "drafted"
    assert _chapter_statuses(initialized_project)[2] == "drafted"


def test_compile_command_rejects_invalid_range_without_partial_success(initialized_project):
    result = run(
        [sys.executable, "-m", "pizhi", "compile", "--chapters", "3-2"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "start must be <= end" in result.stderr
    assert "Traceback" not in result.stderr
