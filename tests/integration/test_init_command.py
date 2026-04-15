from subprocess import run
import sys


def test_cli_shows_top_level_help(project_root):
    result = run(
        [sys.executable, "-m", "pizhi", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "init" in result.stdout
    assert "status" in result.stdout
