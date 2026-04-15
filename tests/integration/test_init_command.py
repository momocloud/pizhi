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


def test_init_creates_expected_project_tree(tmp_path):
    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "init",
            "--project-name",
            "Test Novel",
            "--genre",
            "Crime Fiction",
            "--total-chapters",
            "260",
            "--per-volume",
            "20",
            "--pov",
            "Third Person Limited",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (tmp_path / ".pizhi" / "config.yaml").exists()
    assert (tmp_path / ".pizhi" / "global" / "synopsis.md").exists()
    assert (tmp_path / ".pizhi" / "chapters" / "index.jsonl").exists()
    assert (tmp_path / ".pizhi" / "chapters" / "ch000" / "characters.md").exists()
    assert (tmp_path / ".pizhi" / "hooks" / "pre_chapter.md").exists()
    assert (tmp_path / "manuscript").is_dir()
