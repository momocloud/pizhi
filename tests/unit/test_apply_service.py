from __future__ import annotations

import pytest

from pizhi.services.apply_service import apply_run
from pizhi.services.run_store import RunStore


def _seed_successful_run(
    initialized_project,
    *,
    command: str,
    target: str,
    normalized_text: str,
    metadata: dict[str, object] | None = None,
) -> str:
    store = RunStore(initialized_project / ".pizhi" / "cache" / "runs")
    run_metadata = {"provider": "openai_compatible"}
    if metadata is not None:
        run_metadata.update(metadata)
    record = store.write_success(
        command=command,
        target=target,
        prompt_text="# Prompt",
        raw_payload={"id": "resp_123"},
        normalized_text=normalized_text,
        metadata=run_metadata,
    )
    return record.run_id


def _seed_failed_run(initialized_project, *, status: str) -> str:
    store = RunStore(initialized_project / ".pizhi" / "cache" / "runs")
    record = store.write_failure(
        command="write",
        target="ch001",
        prompt_text="# Prompt",
        error_text="provider failed",
        status=status,
        metadata={"provider": "openai_compatible"},
    )
    return record.run_id


def test_apply_run_routes_successful_write_run(initialized_project, fixture_text):
    run_id = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch001",
        normalized_text=fixture_text("ch001_response.md"),
        metadata={"chapter": 1},
    )

    result = apply_run(initialized_project, run_id)

    assert result.command == "write"
    assert (initialized_project / ".pizhi" / "chapters" / "ch001" / "text.md").exists()


def test_apply_run_rejects_non_success_run(initialized_project):
    run_id = _seed_failed_run(initialized_project, status="provider_failed")

    with pytest.raises(ValueError, match=r"status is provider_failed"):
        apply_run(initialized_project, run_id)
