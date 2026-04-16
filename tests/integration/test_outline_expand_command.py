from subprocess import run
import sys


def test_outline_expand_command_writes_outline_files(initialized_project, project_root):
    response_fixture = project_root / "tests" / "fixtures" / "orchestration" / "outline_expand_response.md"
    response_file = initialized_project / "outline_expand_response.md"
    response_file.write_text(response_fixture.read_text(encoding="utf-8"), encoding="utf-8")

    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "outline",
            "expand",
            "--chapters",
            "1-2",
            "--response-file",
            str(response_file),
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "雨夜访客" in (
        initialized_project / ".pizhi" / "chapters" / "ch001" / "outline.md"
    ).read_text(encoding="utf-8")
    index_text = (initialized_project / ".pizhi" / "chapters" / "index.jsonl").read_text(encoding="utf-8")
    outline_text = (initialized_project / ".pizhi" / "global" / "outline_global.md").read_text(encoding="utf-8")

    assert '"status": "outlined"' in index_text
    assert "雨夜访客" in outline_text
