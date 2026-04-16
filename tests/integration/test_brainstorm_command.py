from pathlib import Path
from subprocess import run
import sys


def test_brainstorm_command_applies_response_file(initialized_project, project_root):
    response_fixture = project_root / "tests" / "fixtures" / "orchestration" / "brainstorm_response.md"
    response_file = initialized_project / "brainstorm_response.md"
    response_file.write_text(response_fixture.read_text(encoding="utf-8"), encoding="utf-8")

    result = run(
        [sys.executable, "-m", "pizhi", "brainstorm", "--response-file", str(response_file)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "故事总体简介" in (initialized_project / ".pizhi" / "global" / "synopsis.md").read_text(encoding="utf-8")
    assert "沈轩" in (initialized_project / ".pizhi" / "chapters" / "ch000" / "characters.md").read_text(encoding="utf-8")
