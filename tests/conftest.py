from pathlib import Path
from subprocess import run
import sys

import pytest


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def fixture_text(project_root):
    def _read(name: str) -> str:
        return (project_root / "tests" / "fixtures" / "chapter_outputs" / name).read_text(encoding="utf-8")

    return _read


@pytest.fixture
def initialized_project(tmp_path) -> Path:
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
    assert result.returncode == 0, result.stderr
    return tmp_path
