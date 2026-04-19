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


def test_apply_command_rejects_missing_run_id(initialized_project):
    result = run(
        [sys.executable, "-m", "pizhi", "apply", "--run-id", "run-missing"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "run run-missing does not exist" in result.stderr
    assert "Traceback" not in result.stderr


def test_apply_command_rejects_structurally_bad_manifest_without_traceback(initialized_project):
    bad_runs = initialized_project / ".pizhi" / "cache" / "runs"

    missing_command_run = bad_runs / "run-missing-command"
    missing_command_run.mkdir(parents=True, exist_ok=True)
    (missing_command_run / "manifest.json").write_text(
        '{"run_id": "run-missing-command", "target": "ch001", "status": "succeeded"}',
        encoding="utf-8",
    )

    malformed_json_run = bad_runs / "run-malformed-json"
    malformed_json_run.mkdir(parents=True, exist_ok=True)
    (malformed_json_run / "manifest.json").write_text("{not json", encoding="utf-8")

    for run_id in ("run-missing-command", "run-malformed-json"):
        result = run(
            [sys.executable, "-m", "pizhi", "apply", "--run-id", run_id],
            cwd=initialized_project,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Traceback" not in result.stderr
        assert "invalid manifest" in result.stderr
