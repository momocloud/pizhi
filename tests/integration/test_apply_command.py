from __future__ import annotations

from subprocess import run
import sys

from pizhi.services.run_store import RunStore


def test_apply_command_rejects_non_success_run(initialized_project):
    store = RunStore(initialized_project / ".pizhi" / "cache" / "runs")
    record = store.write_failure(
        command="write",
        target="ch001",
        prompt_text="# Prompt",
        error_text="provider failed",
        status="provider_failed",
        metadata={"provider": "openai_compatible"},
    )

    result = run(
        [sys.executable, "-m", "pizhi", "apply", "--run-id", record.run_id],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "status is provider_failed" in result.stderr
