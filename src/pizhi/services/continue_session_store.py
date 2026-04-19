from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ContinueSessionRecord:
    session_id: str
    session_dir: Path
    manifest_path: Path
    count: int
    direction: str
    start_chapter: int
    target_end_chapter: int
    current_stage: str
    current_range: tuple[int, int]
    last_checkpoint_id: str | None
    status: str
    created_at: str
    updated_at: str


class ContinueSessionStore:
    def __init__(self, continue_sessions_dir: Path) -> None:
        self.continue_sessions_dir = continue_sessions_dir

    def create(
        self,
        *,
        count: int,
        direction: str,
        start_chapter: int,
        target_end_chapter: int,
        current_stage: str,
        current_range: tuple[int, int],
        last_checkpoint_id: str | None = None,
        status: str,
    ) -> ContinueSessionRecord:
        normalized_current_range = self._validate_int_pair(current_range, field_name="current_range")
        session_id = self._new_session_id()
        session_dir = self.continue_sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        created_at = self._created_at()

        manifest = self._build_manifest(
            session_id=session_id,
            count=count,
            direction=direction,
            start_chapter=start_chapter,
            target_end_chapter=target_end_chapter,
            current_stage=current_stage,
            current_range=normalized_current_range,
            last_checkpoint_id=last_checkpoint_id,
            status=status,
            created_at=created_at,
            updated_at=created_at,
        )
        manifest_path = session_dir / "manifest.json"
        self._write_manifest(manifest_path, manifest)
        return self._record_from_manifest(session_dir=session_dir, manifest=manifest)

    def load(self, session_id: str) -> ContinueSessionRecord:
        session_dir = self.continue_sessions_dir / session_id
        manifest_path = session_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return self._record_from_manifest(session_dir=session_dir, manifest=manifest)

    def update(self, session_id: str, **changes: object) -> ContinueSessionRecord:
        record = self.load(session_id)
        manifest = self._manifest_from_record(record)
        if "current_range" in changes:
            changes = {
                **changes,
                "current_range": list(self._validate_int_pair(changes["current_range"], field_name="current_range")),
            }
        manifest.update(changes)
        manifest["updated_at"] = self._next_updated_at(record.updated_at)
        self._write_manifest(record.manifest_path, manifest)
        return self._record_from_manifest(session_dir=record.session_dir, manifest=manifest)

    def _record_from_manifest(
        self,
        *,
        session_dir: Path,
        manifest: dict[str, object],
    ) -> ContinueSessionRecord:
        current_range = self._validate_int_pair(manifest.get("current_range"), field_name="current_range")
        return ContinueSessionRecord(
            session_id=str(manifest["session_id"]),
            session_dir=session_dir,
            manifest_path=session_dir / "manifest.json",
            count=int(manifest["count"]),
            direction=str(manifest["direction"]),
            start_chapter=int(manifest["start_chapter"]),
            target_end_chapter=int(manifest["target_end_chapter"]),
            current_stage=str(manifest["current_stage"]),
            current_range=current_range,
            last_checkpoint_id=manifest.get("last_checkpoint_id") or None,
            status=str(manifest["status"]),
            created_at=str(manifest["created_at"]),
            updated_at=str(manifest["updated_at"]),
        )

    def _manifest_from_record(self, record: ContinueSessionRecord) -> dict[str, object]:
        return {
            "session_id": record.session_id,
            "count": record.count,
            "direction": record.direction,
            "start_chapter": record.start_chapter,
            "target_end_chapter": record.target_end_chapter,
            "current_stage": record.current_stage,
            "current_range": list(record.current_range),
            "last_checkpoint_id": record.last_checkpoint_id,
            "status": record.status,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    def _build_manifest(
        self,
        *,
        session_id: str,
        count: int,
        direction: str,
        start_chapter: int,
        target_end_chapter: int,
        current_stage: str,
        current_range: tuple[int, int],
        last_checkpoint_id: str | None,
        status: str,
        created_at: str,
        updated_at: str,
    ) -> dict[str, object]:
        normalized_current_range = self._validate_int_pair(current_range, field_name="current_range")
        return {
            "session_id": session_id,
            "count": count,
            "direction": direction,
            "start_chapter": start_chapter,
            "target_end_chapter": target_end_chapter,
            "current_stage": current_stage,
            "current_range": list(normalized_current_range),
            "last_checkpoint_id": last_checkpoint_id,
            "status": status,
            "created_at": created_at,
            "updated_at": updated_at,
        }

    @staticmethod
    def _validate_int_pair(value: object, *, field_name: str) -> tuple[int, int]:
        if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(f"{field_name} must be a pair of integers")

        first, second = value
        if (
            not isinstance(first, int)
            or isinstance(first, bool)
            or not isinstance(second, int)
            or isinstance(second, bool)
        ):
            raise ValueError(f"{field_name} must be a pair of integers")
        return (first, second)

    @staticmethod
    def _write_manifest(manifest_path: Path, manifest: dict[str, object]) -> None:
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    @staticmethod
    def _created_at() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _next_updated_at(previous: str) -> str:
        current = datetime.now(UTC)
        candidate = current.isoformat().replace("+00:00", "Z")
        if candidate != previous:
            return candidate
        return (current.replace(microsecond=current.microsecond + 1)).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _new_session_id() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"session-{timestamp}-{uuid4().hex[:8]}"
