from subprocess import run
import sys


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
