import pytest

from pizhi.core.paths import ProjectPaths
from pizhi.services.continue_session_store import ContinueSessionStore


def test_project_paths_expose_continue_session_dir(tmp_path):
    paths = ProjectPaths(tmp_path)

    assert paths.continue_sessions_dir == tmp_path / ".pizhi" / "cache" / "continue_sessions"


def test_continue_session_store_round_trips_loaded_session(tmp_path):
    store = ContinueSessionStore(tmp_path / ".pizhi" / "cache" / "continue_sessions")
    record = store.create(
        count=3,
        direction="go deeper",
        start_chapter=7,
        target_end_chapter=9,
        current_stage="outline",
        current_range=(7, 9),
        last_checkpoint_id="checkpoint-123",
        status="active",
    )

    loaded = store.load(record.session_id)

    assert loaded.session_id == record.session_id
    assert loaded.session_dir == record.session_dir
    assert loaded.manifest_path == record.manifest_path
    assert loaded.count == 3
    assert loaded.direction == "go deeper"
    assert loaded.start_chapter == 7
    assert loaded.target_end_chapter == 9
    assert loaded.current_stage == "outline"
    assert loaded.current_range == (7, 9)
    assert loaded.last_checkpoint_id == "checkpoint-123"
    assert loaded.status == "active"
    assert loaded.created_at == loaded.updated_at


def test_continue_session_store_updates_status(tmp_path):
    store = ContinueSessionStore(tmp_path / ".pizhi" / "cache" / "continue_sessions")
    record = store.create(
        count=1,
        direction="forward",
        start_chapter=1,
        target_end_chapter=1,
        current_stage="outline",
        current_range=(1, 1),
        last_checkpoint_id=None,
        status="active",
    )

    updated = store.update(record.session_id, status="blocked")

    assert updated.status == "blocked"
    assert updated.updated_at != record.updated_at


def test_continue_session_store_rejects_invalid_current_range_update(tmp_path):
    store = ContinueSessionStore(tmp_path / ".pizhi" / "cache" / "continue_sessions")
    record = store.create(
        count=1,
        direction="forward",
        start_chapter=1,
        target_end_chapter=1,
        current_stage="outline",
        current_range=(1, 1),
        last_checkpoint_id=None,
        status="active",
    )

    with pytest.raises(ValueError, match="current_range must be a pair of integers"):
        store.update(record.session_id, current_range=(1,))


def test_continue_session_store_rejects_invalid_current_range_in_manifest(tmp_path):
    store = ContinueSessionStore(tmp_path / ".pizhi" / "cache" / "continue_sessions")
    record = store.create(
        count=1,
        direction="forward",
        start_chapter=1,
        target_end_chapter=2,
        current_stage="outline",
        current_range=(1, 2),
        last_checkpoint_id=None,
        status="active",
    )

    record.manifest_path.write_text(
        """{
  "session_id": "session-bad",
  "count": 1,
  "direction": "forward",
  "start_chapter": 1,
  "target_end_chapter": 2,
  "current_stage": "outline",
  "current_range": [1],
  "last_checkpoint_id": null,
  "status": "active",
  "created_at": "2026-04-19T00:00:00Z",
  "updated_at": "2026-04-19T00:00:00Z"
}
""",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValueError, match="current_range must be a pair of integers"):
        store.load(record.session_id)
