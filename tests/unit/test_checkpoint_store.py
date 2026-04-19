from pizhi.core.paths import ProjectPaths
from pizhi.services.checkpoint_store import CheckpointStore


def test_project_paths_expose_checkpoint_dir(tmp_path):
    paths = ProjectPaths(tmp_path)

    assert paths.checkpoints_dir == tmp_path / ".pizhi" / "cache" / "checkpoints"


def test_checkpoint_store_round_trips_run_ids_and_status(tmp_path):
    store = CheckpointStore(tmp_path / ".pizhi" / "cache" / "checkpoints")
    record = store.create(
        session_id="session-1",
        stage="outline",
        chapter_range=(4, 6),
        run_ids=["run-1", "run-2"],
        status="generated",
    )

    loaded = store.load(record.checkpoint_id)

    assert loaded.checkpoint_id == record.checkpoint_id
    assert loaded.checkpoint_dir == record.checkpoint_dir
    assert loaded.manifest_path == record.manifest_path
    assert loaded.session_id == "session-1"
    assert loaded.stage == "outline"
    assert loaded.chapter_range == (4, 6)
    assert loaded.run_ids == ["run-1", "run-2"]
    assert loaded.status == "generated"
    assert loaded.applied_at is None


def test_checkpoint_store_updates_status(tmp_path):
    store = CheckpointStore(tmp_path / ".pizhi" / "cache" / "checkpoints")
    record = store.create(
        session_id="session-1",
        stage="write",
        chapter_range=(7, 9),
        run_ids=["run-3"],
        status="generated",
    )

    updated = store.update(record.checkpoint_id, status="applied", applied_at="2026-04-19T10:00:00Z")

    assert updated.status == "applied"
    assert updated.applied_at == "2026-04-19T10:00:00Z"
