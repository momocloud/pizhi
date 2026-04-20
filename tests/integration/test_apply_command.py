from __future__ import annotations

from dataclasses import dataclass
from subprocess import run
import sys

from pizhi.cli import main
from pizhi.services.maintenance import MaintenanceFinding
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.run_store import RunStore


@dataclass(frozen=True, slots=True)
class AppliedRun:
    run_id: str
    command: str
    target: str
    status: str = "succeeded"
    maintenance_result: MaintenanceResult | None = None


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


def test_apply_command_rejects_directory_normalized_md_without_traceback(initialized_project):
    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"
    run_dir = runs_dir / "run-dir-normalized"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        (
            '{"run_id": "run-dir-normalized", "command": "write", "target": "ch001", '
            '"status": "succeeded", "created_at": "2026-04-19T00:00:00Z", '
            '"metadata": {"chapter": 1}, "referenced_files": []}'
        ),
        encoding="utf-8",
    )
    (run_dir / "normalized.md").mkdir()

    result = run(
        [sys.executable, "-m", "pizhi", "apply", "--run-id", "run-dir-normalized"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "normalized.md" in result.stderr


def test_apply_command_prints_write_maintenance_summary(initialized_project, monkeypatch, capsys):
    maintenance_result = MaintenanceResult(
        synopsis_review=None,
        archive_result=None,
        findings=[MaintenanceFinding(category="Maintenance agent", detail="archive.audit: failed - boom")],
    )

    monkeypatch.setattr(
        "pizhi.commands.apply_cmd.apply_run",
        lambda *_args, **_kwargs: AppliedRun(
            run_id="run-123",
            command="write",
            target="ch001",
            maintenance_result=maintenance_result,
        ),
    )

    result = main(["apply", "--run-id", "run-123"])

    captured = capsys.readouterr()
    assert result == 0
    assert "Applied run: run-123 write ch001" in captured.out
    assert "Maintenance agent: archive.audit: failed - boom" in captured.out
