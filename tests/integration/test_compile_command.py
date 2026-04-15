from subprocess import run
import sys

from pizhi.services.chapter_writer import apply_chapter_response


def test_compile_command_writes_volume_file(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "compile"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (initialized_project / "manuscript" / "vol_01.md").exists()
