import sys
from subprocess import run

from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response


def _chapter_statuses(initialized_project) -> dict[int, str]:
    paths = project_paths(initialized_project)
    store = ChapterIndexStore(paths.chapter_index_file)
    return {int(record["n"]): record["status"] for record in store.read_all()}


def _set_chapter_status(initialized_project, chapter_number: int, status: str) -> None:
    paths = project_paths(initialized_project)
    store = ChapterIndexStore(paths.chapter_index_file)
    records = store.read_all()
    for record in records:
        if int(record["n"]) == chapter_number:
            record["status"] = status
            store.upsert(record)
            return
    raise AssertionError(f"missing chapter {chapter_number}")


def _seed_chapters(initialized_project, fixture_text, start: int, end: int) -> None:
    fixture_names = ("ch001_response.md", "ch002_response.md")
    for chapter_number in range(start, end + 1):
        apply_chapter_response(
            initialized_project,
            chapter_number,
            fixture_text(fixture_names[(chapter_number - start) % 2]),
        )


def _set_total_planned(initialized_project, total_planned: int) -> None:
    paths = project_paths(initialized_project)
    config = load_config(paths.config_file)
    config.chapters.total_planned = total_planned
    save_config(paths.config_file, config)


def test_compile_command_writes_volume_file(initialized_project, fixture_text):
    _seed_chapters(initialized_project, fixture_text, 1, 20)
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
    assert _chapter_statuses(initialized_project)[20] == "compiled"
    assert _chapter_statuses(initialized_project)[21] == "drafted"


def test_compile_command_writes_partial_final_volume_file(initialized_project, fixture_text):
    _set_total_planned(initialized_project, 26)
    _seed_chapters(initialized_project, fixture_text, 21, 26)

    result = run(
        [sys.executable, "-m", "pizhi", "compile", "--volume", "2"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (initialized_project / "manuscript" / "vol_02.md").exists()
    assert _chapter_statuses(initialized_project)[21] == "compiled"
    assert _chapter_statuses(initialized_project)[26] == "compiled"


def test_compile_command_rejects_uncompiled_chapter_in_volume(initialized_project, fixture_text):
    _seed_chapters(initialized_project, fixture_text, 1, 20)
    _set_chapter_status(initialized_project, 7, "outlined")

    result = run(
        [sys.executable, "-m", "pizhi", "compile", "--volume", "1"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "ch007 has status outlined" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (initialized_project / "manuscript" / "vol_01.md").exists()
    assert _chapter_statuses(initialized_project)[7] == "outlined"


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


def test_compile_command_rejects_uncompiled_middle_chapter_in_range(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    apply_chapter_response(initialized_project, 3, fixture_text("ch001_response.md"))
    _set_chapter_status(initialized_project, 2, "planned")

    result = run(
        [sys.executable, "-m", "pizhi", "compile", "--chapters", "1-3"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "ch002 has status planned" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (initialized_project / "manuscript" / "ch001-ch003.md").exists()
    assert _chapter_statuses(initialized_project)[2] == "planned"


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
