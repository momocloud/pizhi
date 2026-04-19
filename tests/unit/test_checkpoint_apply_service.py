from __future__ import annotations

from dataclasses import dataclass

import pytest

from pizhi.core.paths import project_paths
from pizhi.services.checkpoint_apply_service import apply_checkpoint
from pizhi.services.checkpoint_store import CheckpointStore
from pizhi.services.continue_session_store import ContinueSessionStore
from pizhi.services.run_store import RunStore


@dataclass(frozen=True, slots=True)
class AppliedRun:
    run_id: str
    command: str = "write"
    target: str = "ch001"
    status: str = "succeeded"


def _seed_successful_run(
    project_root,
    *,
    command: str,
    target: str,
    normalized_text: str,
    metadata: dict[str, object] | None = None,
) -> str:
    store = RunStore(project_paths(project_root).runs_dir)
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


def _create_generated_checkpoint(project_root, *, stage: str, run_ids: list[str]) -> tuple[str, str]:
    session_store = ContinueSessionStore(project_paths(project_root).continue_sessions_dir)
    session = session_store.create(
        count=len(run_ids),
        direction="hold position",
        start_chapter=1,
        target_end_chapter=max(1, len(run_ids)),
        current_stage=stage,
        current_range=(1, max(1, len(run_ids))),
        last_checkpoint_id=None,
        status="waiting_apply",
    )
    checkpoint = CheckpointStore(project_paths(project_root).checkpoints_dir).create(
        session_id=session.session_id,
        stage=stage,
        chapter_range=(1, max(1, len(run_ids))),
        run_ids=run_ids,
        status="generated",
    )
    session_store.update(session.session_id, last_checkpoint_id=checkpoint.checkpoint_id)
    return session.session_id, checkpoint.checkpoint_id


def test_apply_checkpoint_applies_write_runs_in_chapter_order(initialized_project, monkeypatch):
    run_10 = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch010",
        normalized_text="# chapter 10",
        metadata={"chapter": 10},
    )
    run_2 = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch002",
        normalized_text="# chapter 2",
        metadata={"chapter": 2},
    )
    run_6 = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch006",
        normalized_text="# chapter 6",
        metadata={"chapter": 6},
    )
    session_id, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="write",
        run_ids=[run_10, run_2, run_6],
    )

    applied_order: list[str] = []

    def _record_apply(project_root, run_id):
        applied_order.append(run_id)
        return AppliedRun(run_id=run_id)

    monkeypatch.setattr("pizhi.services.checkpoint_apply_service.apply_run", _record_apply)

    result = apply_checkpoint(initialized_project, checkpoint_id)

    assert applied_order == [run_2, run_6, run_10]
    assert result.checkpoint.status == "applied"
    assert result.session.status == "ready_to_resume"
    assert result.checkpoint.applied_at is not None
    assert result.session.last_checkpoint_id == checkpoint_id


def test_apply_checkpoint_stops_on_first_failure(initialized_project, monkeypatch):
    run_1 = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch001",
        normalized_text="# chapter 1",
        metadata={"chapter": 1},
    )
    run_2 = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch002",
        normalized_text="# chapter 2",
        metadata={"chapter": 2},
    )
    session_id, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="write",
        run_ids=[run_1, run_2],
    )

    applied_order: list[str] = []

    def _fail_on_first_apply(project_root, run_id):
        applied_order.append(run_id)
        raise RuntimeError("boom")

    monkeypatch.setattr("pizhi.services.checkpoint_apply_service.apply_run", _fail_on_first_apply)

    with pytest.raises(RuntimeError, match="boom"):
        apply_checkpoint(initialized_project, checkpoint_id)

    checkpoint = CheckpointStore(project_paths(initialized_project).checkpoints_dir).load(checkpoint_id)
    session = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir).load(session_id)
    assert applied_order == [run_1]
    assert checkpoint.status == "failed"
    assert checkpoint.applied_at is None
    assert session.status == "blocked"
    assert session.last_checkpoint_id == checkpoint_id


def test_apply_checkpoint_appends_split_outline_blocks(initialized_project, fixture_text):
    run_1 = _seed_successful_run(
        initialized_project,
        command="outline-expand",
        target="ch001",
        normalized_text=fixture_text("outline_expand_response.md").split("\n\n## ch002", 1)[0].strip(),
    )
    run_2 = _seed_successful_run(
        initialized_project,
        command="outline-expand",
        target="ch002",
        normalized_text="## ch002 | 码头血衣\n- 沈轩追查到旧港仓库。\n- 顾临发现血衣与旧案编号重合。\n",
    )
    _, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="outline",
        run_ids=[run_1, run_2],
    )

    apply_checkpoint(initialized_project, checkpoint_id)

    outline_text = (initialized_project / ".pizhi" / "global" / "outline_global.md").read_text(encoding="utf-8")
    assert "## ch001 | 雨夜访客" in outline_text
    assert "## ch002 | 码头血衣" in outline_text
    assert outline_text.index("## ch001 | 雨夜访客") < outline_text.index("## ch002 | 码头血衣")


def test_apply_checkpoint_rejects_non_generated_checkpoint(initialized_project):
    session_store = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir)
    session = session_store.create(
        count=1,
        direction="hold position",
        start_chapter=1,
        target_end_chapter=1,
        current_stage="write",
        current_range=(1, 1),
        last_checkpoint_id=None,
        status="ready_to_resume",
    )
    checkpoint = CheckpointStore(project_paths(initialized_project).checkpoints_dir).create(
        session_id=session.session_id,
        stage="write",
        chapter_range=(1, 1),
        run_ids=[],
        status="failed",
    )

    with pytest.raises(ValueError, match=r"checkpoint .* status is failed"):
        apply_checkpoint(initialized_project, checkpoint.checkpoint_id)
