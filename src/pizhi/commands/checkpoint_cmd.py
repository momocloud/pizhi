from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
import json
import sys
from pathlib import Path
from uuid import uuid4

from pizhi.core.paths import project_paths


@dataclass(frozen=True, slots=True)
class ContinueSessionRecord:
    session_id: str
    checkpoint_id: str
    stage: str
    status: str
    count: int
    chapter_range: tuple[int, int]
    direction: str
    run_id: str | None
    prompt_packet_id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ContinueCheckpointRecord:
    checkpoint_id: str
    session_id: str
    stage: str
    status: str
    chapter_range: tuple[int, int]
    run_id: str | None
    prompt_packet_id: str
    normalized_text: str
    created_at: str
    updated_at: str


def create_continue_session(
    project_root: Path,
    *,
    checkpoint_id: str,
    chapter_range: tuple[int, int],
    count: int,
    direction: str,
    run_id: str | None,
    prompt_packet_id: str,
) -> ContinueSessionRecord:
    session_id = _new_id("session")
    created_at = _timestamp()
    record = ContinueSessionRecord(
        session_id=session_id,
        checkpoint_id=checkpoint_id,
        stage="continue",
        status="pending",
        count=count,
        chapter_range=chapter_range,
        direction=direction,
        run_id=run_id,
        prompt_packet_id=prompt_packet_id,
        created_at=created_at,
        updated_at=created_at,
    )
    _write_record(_sessions_dir(project_root) / f"{record.session_id}.json", record)
    return record


def create_continue_checkpoint(
    project_root: Path,
    *,
    checkpoint_id: str,
    session_id: str,
    chapter_range: tuple[int, int],
    run_id: str | None,
    prompt_packet_id: str,
    normalized_text: str,
) -> ContinueCheckpointRecord:
    created_at = _timestamp()
    record = ContinueCheckpointRecord(
        checkpoint_id=checkpoint_id,
        session_id=session_id,
        stage="outline",
        status="pending",
        chapter_range=chapter_range,
        run_id=run_id,
        prompt_packet_id=prompt_packet_id,
        normalized_text=normalized_text,
        created_at=created_at,
        updated_at=created_at,
    )
    _write_record(_checkpoints_dir(project_root) / f"{record.checkpoint_id}.json", record)
    return record


def list_continue_sessions(project_root: Path) -> list[ContinueSessionRecord]:
    sessions_dir = _sessions_dir(project_root)
    if not sessions_dir.exists():
        return []
    records = [_read_session_record(path) for path in sorted(sessions_dir.glob("*.json"))]
    return sorted(records, key=lambda record: record.created_at)


def list_checkpoints(project_root: Path, session_id: str) -> list[ContinueCheckpointRecord]:
    checkpoints_dir = _checkpoints_dir(project_root)
    if not checkpoints_dir.exists():
        return []
    records = []
    for path in sorted(checkpoints_dir.glob("*.json")):
        data = _read_json(path)
        if data.get("session_id") == session_id:
            records.append(_read_checkpoint_record(path))
    return sorted(records, key=lambda record: record.created_at)


def apply_checkpoint(project_root: Path, checkpoint_id: str) -> ContinueCheckpointRecord:
    checkpoint_path = _checkpoints_dir(project_root) / f"{checkpoint_id}.json"
    if not checkpoint_path.exists():
        raise ValueError(f"checkpoint {checkpoint_id} does not exist")

    record = _read_checkpoint_record(checkpoint_path)
    updated = ContinueCheckpointRecord(
        checkpoint_id=record.checkpoint_id,
        session_id=record.session_id,
        stage=record.stage,
        status="applied",
        chapter_range=record.chapter_range,
        run_id=record.run_id,
        prompt_packet_id=record.prompt_packet_id,
        normalized_text=record.normalized_text,
        created_at=record.created_at,
        updated_at=_timestamp(),
    )
    _write_record(checkpoint_path, updated)
    _update_session_status(project_root, record.session_id, "checkpoint_applied")
    return updated


def resume_continue_execution(project_root: Path, session_id: str) -> ContinueSessionRecord:
    session_path = _sessions_dir(project_root) / f"{session_id}.json"
    if not session_path.exists():
        raise ValueError(f"session {session_id} does not exist")

    record = _read_session_record(session_path)
    checkpoint_path = _checkpoints_dir(project_root) / f"{record.checkpoint_id}.json"
    if not checkpoint_path.exists():
        raise ValueError(f"checkpoint {record.checkpoint_id} does not exist")
    checkpoint = _read_checkpoint_record(checkpoint_path)
    if checkpoint.status != "applied":
        raise ValueError(f"checkpoint {checkpoint.checkpoint_id} is {checkpoint.status}")

    updated = ContinueSessionRecord(
        session_id=record.session_id,
        checkpoint_id=record.checkpoint_id,
        stage=record.stage,
        status="resumed",
        count=record.count,
        chapter_range=record.chapter_range,
        direction=record.direction,
        run_id=record.run_id,
        prompt_packet_id=record.prompt_packet_id,
        created_at=record.created_at,
        updated_at=_timestamp(),
    )
    _write_record(session_path, updated)
    return updated


def run_checkpoint_apply(args) -> int:
    try:
        record = apply_checkpoint(Path.cwd(), args.id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Checkpoint ID: {record.checkpoint_id}")
    print(f"Session ID: {record.session_id}")
    print(f"Stage: {record.stage}")
    print(f"Status: {record.status}")
    return 0


def run_checkpoints(args) -> int:
    records = list_checkpoints(Path.cwd(), args.session_id)
    for record in records:
        print(f"Checkpoint ID: {record.checkpoint_id}")
        print(f"Session ID: {record.session_id}")
        print(f"Stage: {record.stage}")
        print(f"Status: {record.status}")
        print(f"Created At: {record.created_at}")
        print("")
    return 0


def _sessions_dir(project_root: Path) -> Path:
    return project_paths(project_root).cache_dir / "continue" / "sessions"


def _checkpoints_dir(project_root: Path) -> Path:
    return project_paths(project_root).cache_dir / "continue" / "checkpoints"


def _write_record(path: Path, record: ContinueSessionRecord | ContinueCheckpointRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_session_record(path: Path) -> ContinueSessionRecord:
    data = _read_json(path)
    return ContinueSessionRecord(
        session_id=str(data["session_id"]),
        checkpoint_id=str(data["checkpoint_id"]),
        stage=str(data["stage"]),
        status=str(data["status"]),
        count=int(data["count"]),
        chapter_range=(int(data["chapter_range"][0]), int(data["chapter_range"][1])),
        direction=str(data["direction"]),
        run_id=(None if data.get("run_id") in (None, "") else str(data["run_id"])),
        prompt_packet_id=str(data["prompt_packet_id"]),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
    )


def _read_checkpoint_record(path: Path) -> ContinueCheckpointRecord:
    data = _read_json(path)
    return ContinueCheckpointRecord(
        checkpoint_id=str(data["checkpoint_id"]),
        session_id=str(data["session_id"]),
        stage=str(data["stage"]),
        status=str(data["status"]),
        chapter_range=(int(data["chapter_range"][0]), int(data["chapter_range"][1])),
        run_id=(None if data.get("run_id") in (None, "") else str(data["run_id"])),
        prompt_packet_id=str(data["prompt_packet_id"]),
        normalized_text=str(data["normalized_text"]),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
    )


def _update_session_status(project_root: Path, session_id: str, status: str) -> None:
    session_path = _sessions_dir(project_root) / f"{session_id}.json"
    if not session_path.exists():
        return
    record = _read_session_record(session_path)
    updated = ContinueSessionRecord(
        session_id=record.session_id,
        checkpoint_id=record.checkpoint_id,
        stage=record.stage,
        status=status,
        count=record.count,
        chapter_range=record.chapter_range,
        direction=record.direction,
        run_id=record.run_id,
        prompt_packet_id=record.prompt_packet_id,
        created_at=record.created_at,
        updated_at=_timestamp(),
    )
    _write_record(session_path, updated)


def _new_id(prefix: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{timestamp}-{uuid4().hex[:8]}"


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
