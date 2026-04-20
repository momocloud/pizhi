from __future__ import annotations

from dataclasses import dataclass

import pytest

from pizhi.core.paths import project_paths
from pizhi.services import checkpoint_apply_service
from pizhi.services.checkpoint_apply_service import apply_checkpoint
from pizhi.services.checkpoint_store import CheckpointStore
from pizhi.services.continue_session_store import ContinueSessionStore
from pizhi.services.maintenance import MaintenanceFinding
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.run_store import RunStore


@dataclass(frozen=True, slots=True)
class AppliedRun:
    run_id: str
    command: str = "write"
    target: str = "ch001"
    status: str = "succeeded"
    maintenance_result: MaintenanceResult | None = None


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


def test_apply_checkpoint_returns_write_run_maintenance_results_in_chapter_order(initialized_project, monkeypatch):
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
    _, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="write",
        run_ids=[run_10, run_2],
    )

    maintenance_2 = MaintenanceResult(
        synopsis_review=None,
        archive_result=None,
        findings=[MaintenanceFinding(category="Maintenance agent", detail="archive.audit: failed - boom")],
    )
    maintenance_10 = MaintenanceResult(
        synopsis_review=None,
        archive_result=None,
        findings=[MaintenanceFinding(category="Maintenance agent", detail="archive.audit: promoted")],
    )

    def _record_apply(project_root, run_id):
        if run_id == run_2:
            return AppliedRun(run_id=run_id, maintenance_result=maintenance_2)
        return AppliedRun(run_id=run_id, maintenance_result=maintenance_10)

    monkeypatch.setattr("pizhi.services.checkpoint_apply_service.apply_run", _record_apply)

    result = apply_checkpoint(initialized_project, checkpoint_id)

    assert result.maintenance_results == [(2, maintenance_2), (10, maintenance_10)]


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


def test_apply_checkpoint_rolls_back_true_source_on_late_failure(initialized_project, monkeypatch, fixture_text):
    chapter_dir = project_paths(initialized_project).chapter_dir(1)
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "text.md").write_text("PREEXISTING\n", encoding="utf-8", newline="\n")
    (chapter_dir / "meta.json").write_text('{"preexisting": true}\n', encoding="utf-8", newline="\n")

    run_1 = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch001",
        normalized_text=fixture_text("ch001_response.md"),
        metadata={"chapter": 1},
    )
    run_2 = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch002",
        normalized_text=fixture_text("ch002_response.md"),
        metadata={"chapter": 2},
    )
    session_id, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="write",
        run_ids=[run_1, run_2],
    )

    call_count = 0
    original_apply_run = checkpoint_apply_service.apply_run

    def _apply_then_fail(project_root, run_id):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return original_apply_run(project_root, run_id)
        raise RuntimeError("boom")

    monkeypatch.setattr("pizhi.services.checkpoint_apply_service.apply_run", _apply_then_fail)

    with pytest.raises(RuntimeError, match="boom"):
        apply_checkpoint(initialized_project, checkpoint_id)

    checkpoint = CheckpointStore(project_paths(initialized_project).checkpoints_dir).load(checkpoint_id)
    session = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir).load(session_id)
    assert (chapter_dir / "text.md").read_text(encoding="utf-8") == "PREEXISTING\n"
    assert not (chapter_dir / "worldview_patch.md").exists()
    assert (chapter_dir / "meta.json").read_text(encoding="utf-8") == '{"preexisting": true}\n'
    assert checkpoint.status == "failed"
    assert session.status == "blocked"


def test_apply_checkpoint_restores_truth_source_and_manifests_when_finalize_fails(
    initialized_project, monkeypatch, fixture_text
):
    chapter_dir = project_paths(initialized_project).chapter_dir(1)
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "text.md").write_text("PREEXISTING\n", encoding="utf-8", newline="\n")
    (chapter_dir / "meta.json").write_text('{"preexisting": true}\n', encoding="utf-8", newline="\n")

    run_id = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch001",
        normalized_text=fixture_text("ch001_response.md"),
        metadata={"chapter": 1},
    )
    session_id, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="write",
        run_ids=[run_id],
    )

    original_update = checkpoint_apply_service.ContinueSessionStore.update

    def _fail_ready_to_resume(self, session_id, **changes):
        if changes.get("status") == "ready_to_resume":
            raise RuntimeError("finalize boom")
        return original_update(self, session_id, **changes)

    monkeypatch.setattr(
        checkpoint_apply_service.ContinueSessionStore,
        "update",
        _fail_ready_to_resume,
    )

    with pytest.raises(RuntimeError, match="finalize boom"):
        apply_checkpoint(initialized_project, checkpoint_id)

    checkpoint = CheckpointStore(project_paths(initialized_project).checkpoints_dir).load(checkpoint_id)
    session = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir).load(session_id)
    assert (chapter_dir / "text.md").read_text(encoding="utf-8") == "PREEXISTING\n"
    assert not (chapter_dir / "worldview_patch.md").exists()
    assert (chapter_dir / "meta.json").read_text(encoding="utf-8") == '{"preexisting": true}\n'
    assert checkpoint.status == "generated"
    assert checkpoint.applied_at is None
    assert session.status == "waiting_apply"
    assert session.last_checkpoint_id == checkpoint_id


@pytest.mark.parametrize("mutate_manifest", ["bad_target", "broken_manifest"])
def test_apply_checkpoint_marks_failed_blocked_when_sorting_fails(initialized_project, mutate_manifest):
    run_id = _seed_successful_run(
        initialized_project,
        command="write",
        target="ch001",
        normalized_text="# chapter 1",
        metadata={"chapter": 1},
    )
    run_dir = project_paths(initialized_project).runs_dir / run_id
    manifest_path = run_dir / "manifest.json"
    if mutate_manifest == "bad_target":
        manifest_text = manifest_path.read_text(encoding="utf-8").replace('"target": "ch001"', '"target": "not-a-target"')
        manifest_path.write_text(manifest_text, encoding="utf-8", newline="\n")
    else:
        manifest_path.write_text("{not json}\n", encoding="utf-8", newline="\n")

    session_id, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="write",
        run_ids=[run_id],
    )

    with pytest.raises(Exception):
        apply_checkpoint(initialized_project, checkpoint_id)

    checkpoint = CheckpointStore(project_paths(initialized_project).checkpoints_dir).load(checkpoint_id)
    session = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir).load(session_id)
    assert checkpoint.status == "failed"
    assert session.status == "blocked"


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


def test_apply_checkpoint_replaces_duplicate_outline_blocks_in_global_outline(initialized_project):
    run_1 = _seed_successful_run(
        initialized_project,
        command="outline-expand",
        target="ch001",
        normalized_text=(
            "## ch001 | 旧标题\n"
            "- old beat\n"
        ),
    )
    run_2 = _seed_successful_run(
        initialized_project,
        command="outline-expand",
        target="ch001",
        normalized_text=(
            "## ch001 | 新标题\n"
            "- new beat\n"
        ),
    )
    _, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="outline",
        run_ids=[run_1, run_2],
    )

    apply_checkpoint(initialized_project, checkpoint_id)

    outline_text = (initialized_project / ".pizhi" / "global" / "outline_global.md").read_text(encoding="utf-8")
    assert outline_text.count("## ch001 |") == 1
    assert "## ch001 | 新标题" in outline_text
    assert "- new beat" in outline_text
    assert "旧标题" not in outline_text


def test_apply_checkpoint_preserves_existing_non_chapter_outline_prefix(initialized_project):
    outline_path = initialized_project / ".pizhi" / "global" / "outline_global.md"
    outline_path.write_text(
        "# Global Outline\n\n"
        "## 第一卷\n"
        "- 前言\n"
        "- 旧的大纲前言\n",
        encoding="utf-8",
        newline="\n",
    )

    run_1 = _seed_successful_run(
        initialized_project,
        command="outline-expand",
        target="ch001",
        normalized_text=(
            "## ch001 | 雨夜访客\n"
            "- 雨夜里，沈轩目击第一起命案。\n"
        ),
    )
    _, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="outline",
        run_ids=[run_1],
    )

    apply_checkpoint(initialized_project, checkpoint_id)

    outline_text = outline_path.read_text(encoding="utf-8")
    assert "## 第一卷" in outline_text
    assert "- 旧的大纲前言" in outline_text
    assert "## ch001 | 雨夜访客" in outline_text


def test_apply_checkpoint_keeps_chapter_body_headings_out_of_suffix_detection(initialized_project):
    outline_path = initialized_project / ".pizhi" / "global" / "outline_global.md"
    outline_path.write_text(
        "# Global Outline\n\n"
        "## 第一卷\n"
        "- 前言\n"
        "\n"
        "## ch001 | 雨夜访客\n"
        "- 第一段。\n"
        "## 线索\n"
        "- 章节正文里的二级标题。\n"
        "\n"
        "## ch002 | 码头血衣\n"
        "- 旧的第二章内容。\n",
        encoding="utf-8",
        newline="\n",
    )

    run_2 = _seed_successful_run(
        initialized_project,
        command="outline-expand",
        target="ch002",
        normalized_text=(
            "## ch002 | 码头血衣\n"
            "- 新的第二章内容。\n"
        ),
    )
    _, checkpoint_id = _create_generated_checkpoint(
        initialized_project,
        stage="outline",
        run_ids=[run_2],
    )

    apply_checkpoint(initialized_project, checkpoint_id)

    outline_text = outline_path.read_text(encoding="utf-8")
    assert outline_text.count("## ch002 |") == 1
    assert "## 线索" in outline_text
    assert "- 章节正文里的二级标题。" in outline_text
    assert "- 新的第二章内容。" in outline_text


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
