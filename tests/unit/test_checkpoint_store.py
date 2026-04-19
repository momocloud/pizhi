import pytest

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
    assert loaded.run_ids == ("run-1", "run-2")
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


def test_checkpoint_store_rejects_string_run_ids_update(tmp_path):
    store = CheckpointStore(tmp_path / ".pizhi" / "cache" / "checkpoints")
    record = store.create(
        session_id="session-1",
        stage="write",
        chapter_range=(7, 9),
        run_ids=["run-3"],
        status="generated",
    )
    original_manifest = record.manifest_path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown update fields: run_ids"):
        store.update(record.checkpoint_id, run_ids="run-2")
    assert record.manifest_path.read_text(encoding="utf-8") == original_manifest


def test_checkpoint_store_rejects_invalid_chapter_range_in_manifest(tmp_path):
    store = CheckpointStore(tmp_path / ".pizhi" / "cache" / "checkpoints")
    record = store.create(
        session_id="session-1",
        stage="write",
        chapter_range=(7, 9),
        run_ids=["run-3"],
        status="generated",
    )

    record.manifest_path.write_text(
        """{
  "checkpoint_id": "checkpoint-bad-range",
  "session_id": "session-1",
  "stage": "write",
  "chapter_range": [7],
  "run_ids": ["run-3"],
  "status": "generated",
  "created_at": "2026-04-19T00:00:00Z",
  "applied_at": null
}
""",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValueError, match="chapter_range must be a pair of integers"):
        store.load(record.checkpoint_id)


def test_checkpoint_store_rejects_invalid_run_ids_in_manifest(tmp_path):
    store = CheckpointStore(tmp_path / ".pizhi" / "cache" / "checkpoints")
    record = store.create(
        session_id="session-1",
        stage="outline",
        chapter_range=(4, 6),
        run_ids=["run-1", "run-2"],
        status="generated",
    )

    record.manifest_path.write_text(
        """{
  "checkpoint_id": "checkpoint-bad",
  "session_id": "session-1",
  "stage": "outline",
  "chapter_range": [4, 6],
  "run_ids": "run-2",
  "status": "generated",
  "created_at": "2026-04-19T00:00:00Z",
  "applied_at": null
}
""",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValueError, match="run_ids must be a sequence of strings"):
        store.load(record.checkpoint_id)


def test_checkpoint_store_rejects_unknown_update_field_and_preserves_manifest(tmp_path):
    store = CheckpointStore(tmp_path / ".pizhi" / "cache" / "checkpoints")
    record = store.create(
        session_id="session-1",
        stage="write",
        chapter_range=(7, 9),
        run_ids=["run-3"],
        status="generated",
    )
    original_manifest = record.manifest_path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown update fields: created_at"):
        store.update(record.checkpoint_id, created_at={"bad": "type"})

    assert record.manifest_path.read_text(encoding="utf-8") == original_manifest


def test_checkpoint_store_rejects_invalid_scalar_update_and_preserves_manifest(tmp_path):
    store = CheckpointStore(tmp_path / ".pizhi" / "cache" / "checkpoints")
    record = store.create(
        session_id="session-1",
        stage="write",
        chapter_range=(7, 9),
        run_ids=["run-3"],
        status="generated",
    )
    original_manifest = record.manifest_path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="status must be a string"):
        store.update(record.checkpoint_id, status={"bad": "type"})

    assert record.manifest_path.read_text(encoding="utf-8") == original_manifest
