from __future__ import annotations

from subprocess import run
import sys

from pizhi.services.run_store import RunStore


def test_runs_command_lists_recent_runs(initialized_project):
    store = RunStore(initialized_project / ".pizhi" / "cache" / "runs")
    store.write_success(
        command="brainstorm",
        target="project",
        prompt_text="# Prompt",
        raw_payload={"id": "resp_123"},
        normalized_text="## normalized\n",
        metadata={"provider": "openai_compatible"},
    )

    result = run(
        [sys.executable, "-m", "pizhi", "runs"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "brainstorm" in result.stdout
    assert "succeeded" in result.stdout


def test_runs_command_rejects_bad_manifest_without_traceback(initialized_project):
    runs_dir = initialized_project / ".pizhi" / "cache" / "runs" / "run-bad"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "manifest.json").write_text("{not json", encoding="utf-8")

    result = run(
        [sys.executable, "-m", "pizhi", "runs"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "unable to list runs" in result.stderr
