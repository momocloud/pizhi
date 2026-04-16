from subprocess import run
import sys


def test_write_command_applies_response_file(initialized_project, fixture_text):
    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
        encoding="utf-8",
    )

    response_file = initialized_project / "ch001_response.md"
    response_file.write_text(fixture_text("ch001_response.md"), encoding="utf-8")

    result = run(
        [sys.executable, "-m", "pizhi", "write", "--chapter", "1", "--response-file", str(response_file)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (chapter_dir / "text.md").exists()
    index_text = (initialized_project / ".pizhi" / "chapters" / "index.jsonl").read_text(encoding="utf-8")
    assert '"status": "drafted"' in index_text
