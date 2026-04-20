from __future__ import annotations

import pytest

from pizhi.services.apply_service import apply_run
from pizhi.services.maintenance import MaintenanceFinding
from pizhi.services.maintenance import MaintenanceResult
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


def test_apply_run_routes_successful_brainstorm_run(initialized_project, fixture_text):
    run_id = _seed_successful_run(
        initialized_project,
        command="brainstorm",
        target="project",
        normalized_text=fixture_text("brainstorm_response.md"),
    )

    result = apply_run(initialized_project, run_id)

    assert result.command == "brainstorm"
    assert (initialized_project / ".pizhi" / "global" / "synopsis.md").exists()


def test_apply_run_routes_successful_outline_expand_run(initialized_project, fixture_text):
    run_id = _seed_successful_run(
        initialized_project,
        command="outline-expand",
        target="ch001-ch002",
        normalized_text=fixture_text("outline_expand_response.md"),
    )

    result = apply_run(initialized_project, run_id)

    assert result.command == "outline-expand"
    assert (initialized_project / ".pizhi" / "chapters" / "ch001" / "outline.md").exists()


def test_apply_run_routes_successful_write_run(initialized_project, fixture_text, monkeypatch):
    run_id = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch001",
        normalized_text=fixture_text("ch001_response.md"),
        metadata={"chapter": 1},
    )
    maintenance_result = MaintenanceResult(
        synopsis_review=None,
        archive_result=None,
        findings=[MaintenanceFinding(category="Maintenance agent", detail="archive.audit: failed - boom")],
    )

    monkeypatch.setattr("pizhi.services.write_service.run_after_write", lambda *_args, **_kwargs: maintenance_result)

    result = apply_run(initialized_project, run_id)

    assert result.command == "write"
    assert result.maintenance_result is maintenance_result
    assert (initialized_project / ".pizhi" / "chapters" / "ch001" / "text.md").exists()


def test_apply_run_rejects_non_success_run(initialized_project):
    run_id = _seed_failed_run(initialized_project, status="provider_failed")

    with pytest.raises(ValueError, match=r"status is provider_failed"):
        apply_run(initialized_project, run_id)


def test_apply_run_rejects_missing_run_id(initialized_project):
    with pytest.raises(ValueError, match=r"run run-missing does not exist"):
        apply_run(initialized_project, "run-missing")


def test_apply_run_rejects_missing_normalized_md(initialized_project, fixture_text):
    run_id = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch001",
        normalized_text=fixture_text("ch001_response.md"),
        metadata={"chapter": 1},
    )
    run_dir = initialized_project / ".pizhi" / "cache" / "runs" / run_id
    (run_dir / "normalized.md").unlink()

    with pytest.raises(ValueError, match=r"run .* is missing normalized\.md"):
        apply_run(initialized_project, run_id)


@pytest.mark.parametrize("metadata", [{}, {"chapter": "abc"}])
def test_apply_run_rejects_malformed_write_chapter_metadata(initialized_project, fixture_text, metadata):
    run_id = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch001",
        normalized_text=fixture_text("ch001_response.md"),
        metadata=metadata,
    )

    with pytest.raises(ValueError, match=r"run .* has invalid chapter metadata"):
        apply_run(initialized_project, run_id)
