from __future__ import annotations

import pytest

from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.compiler import CompileTarget
from pizhi.services.compiler import compile_manuscript


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


def test_compile_target_rejects_invalid_field_combinations():
    with pytest.raises(ValueError, match="exactly one"):
        CompileTarget()

    with pytest.raises(ValueError, match="exactly one"):
        CompileTarget(volume=1, chapter=2)

    with pytest.raises(ValueError, match="range start must be <= end"):
        CompileTarget(chapter_start=3, chapter_end=2)


def test_compile_manuscript_writes_volume_target_and_marks_only_selected_chapters(initialized_project, fixture_text):
    _seed_chapters(initialized_project, fixture_text, 1, 20)
    apply_chapter_response(initialized_project, 21, fixture_text("ch001_response.md"))

    written = compile_manuscript(initialized_project, target=CompileTarget(volume=1))

    assert written == [initialized_project / "manuscript" / "vol_01.md"]
    assert (initialized_project / "manuscript" / "vol_01.md").read_text(encoding="utf-8").startswith("# Volume 01")
    assert _chapter_statuses(initialized_project)[1] == "compiled"
    assert _chapter_statuses(initialized_project)[20] == "compiled"
    assert _chapter_statuses(initialized_project)[21] == "drafted"


def test_compile_manuscript_rejects_outlined_chapter_in_volume_target(initialized_project, fixture_text):
    _seed_chapters(initialized_project, fixture_text, 1, 20)
    _set_chapter_status(initialized_project, 7, "outlined")

    with pytest.raises(ValueError, match="ch007 has status outlined"):
        compile_manuscript(initialized_project, target=CompileTarget(volume=1))

    assert not (initialized_project / "manuscript" / "vol_01.md").exists()
    assert _chapter_statuses(initialized_project)[1] == "drafted"
    assert _chapter_statuses(initialized_project)[7] == "outlined"


def test_compile_manuscript_writes_single_chapter_target(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    written = compile_manuscript(initialized_project, target=CompileTarget(chapter=2))

    assert written == [initialized_project / "manuscript" / "ch002.md"]
    assert (initialized_project / "manuscript" / "ch002.md").read_text(encoding="utf-8").startswith("# Chapter 002")
    assert _chapter_statuses(initialized_project)[1] == "drafted"
    assert _chapter_statuses(initialized_project)[2] == "compiled"


def test_compile_manuscript_writes_chapter_range_target(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    apply_chapter_response(initialized_project, 3, fixture_text("ch001_response.md"))

    written = compile_manuscript(initialized_project, target=CompileTarget(chapter_start=2, chapter_end=3))

    assert written == [initialized_project / "manuscript" / "ch002-ch003.md"]
    assert (initialized_project / "manuscript" / "ch002-ch003.md").read_text(encoding="utf-8").startswith("# Chapters 002-003")
    assert _chapter_statuses(initialized_project)[1] == "drafted"
    assert _chapter_statuses(initialized_project)[2] == "compiled"
    assert _chapter_statuses(initialized_project)[3] == "compiled"


def test_compile_manuscript_rejects_uncompiled_middle_chapter_in_range(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    apply_chapter_response(initialized_project, 3, fixture_text("ch001_response.md"))
    _set_chapter_status(initialized_project, 2, "planned")

    with pytest.raises(ValueError, match="ch002 has status planned"):
        compile_manuscript(initialized_project, target=CompileTarget(chapter_start=1, chapter_end=3))

    assert not (initialized_project / "manuscript" / "ch001-ch003.md").exists()
    assert _chapter_statuses(initialized_project)[1] == "drafted"
    assert _chapter_statuses(initialized_project)[2] == "planned"
    assert _chapter_statuses(initialized_project)[3] == "drafted"


def test_compile_manuscript_fails_when_selected_text_is_missing(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    chapter_two_text = initialized_project / ".pizhi" / "chapters" / "ch002" / "text.md"
    chapter_two_text.unlink()

    with pytest.raises(FileNotFoundError, match="ch002.*text\\.md"):
        compile_manuscript(initialized_project, target=CompileTarget(chapter_start=1, chapter_end=2))

    assert not (initialized_project / "manuscript" / "ch001-ch002.md").exists()
    assert _chapter_statuses(initialized_project)[1] == "drafted"
    assert _chapter_statuses(initialized_project)[2] == "drafted"
