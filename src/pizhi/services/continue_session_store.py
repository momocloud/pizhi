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
    _MANIFEST_FIELDS = frozenset(
        {
            "session_id",
            "count",
            "direction",
            "start_chapter",
            "target_end_chapter",
            "current_stage",
            "current_range",
            "last_checkpoint_id",
            "status",
            "created_at",
            "updated_at",
        }
    )
    _UPDATE_FIELDS = frozenset({"current_stage", "current_range", "last_checkpoint_id", "status"})

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
            current_range=current_range,
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
        manifest.update(self._normalize_update_changes(changes))
        manifest["updated_at"] = self._next_updated_at(record.updated_at)
        normalized_manifest = self._normalize_manifest(manifest)
        self._write_manifest(record.manifest_path, normalized_manifest)
        return self._record_from_manifest(session_dir=record.session_dir, manifest=normalized_manifest)

    def _record_from_manifest(
        self,
        *,
        session_dir: Path,
        manifest: dict[str, object],
    ) -> ContinueSessionRecord:
        normalized_manifest = self._normalize_manifest(manifest)
        return ContinueSessionRecord(
            session_id=normalized_manifest["session_id"],
            session_dir=session_dir,
            manifest_path=session_dir / "manifest.json",
            count=normalized_manifest["count"],
            direction=normalized_manifest["direction"],
            start_chapter=normalized_manifest["start_chapter"],
            target_end_chapter=normalized_manifest["target_end_chapter"],
            current_stage=normalized_manifest["current_stage"],
            current_range=tuple(normalized_manifest["current_range"]),
            last_checkpoint_id=normalized_manifest["last_checkpoint_id"],
            status=normalized_manifest["status"],
            created_at=normalized_manifest["created_at"],
            updated_at=normalized_manifest["updated_at"],
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
        return self._normalize_manifest(
            {
            "session_id": session_id,
            "count": count,
            "direction": direction,
            "start_chapter": start_chapter,
            "target_end_chapter": target_end_chapter,
            "current_stage": current_stage,
            "current_range": current_range,
            "last_checkpoint_id": last_checkpoint_id,
            "status": status,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        )

    def _normalize_update_changes(self, changes: dict[str, object]) -> dict[str, object]:
        unknown_fields = sorted(set(changes) - self._UPDATE_FIELDS)
        if unknown_fields:
            raise ValueError(f"Unknown update fields: {', '.join(unknown_fields)}")

        normalized_changes: dict[str, object] = {}
        for field_name, value in changes.items():
            if field_name == "current_stage":
                normalized_changes[field_name] = self._validate_str(value, field_name=field_name)
            elif field_name == "current_range":
                normalized_changes[field_name] = list(self._validate_int_pair(value, field_name=field_name))
            elif field_name == "last_checkpoint_id":
                normalized_changes[field_name] = self._validate_optional_str(value, field_name=field_name)
            elif field_name == "status":
                normalized_changes[field_name] = self._validate_str(value, field_name=field_name)
        return normalized_changes

    def _normalize_manifest(self, manifest: dict[str, object]) -> dict[str, object]:
        self._validate_manifest_keys(manifest)
        current_range = self._validate_int_pair(manifest["current_range"], field_name="current_range")
        return {
            "session_id": self._validate_str(manifest["session_id"], field_name="session_id"),
            "count": self._validate_int(manifest["count"], field_name="count"),
            "direction": self._validate_str(manifest["direction"], field_name="direction"),
            "start_chapter": self._validate_int(manifest["start_chapter"], field_name="start_chapter"),
            "target_end_chapter": self._validate_int(
                manifest["target_end_chapter"], field_name="target_end_chapter"
            ),
            "current_stage": self._validate_str(manifest["current_stage"], field_name="current_stage"),
            "current_range": list(current_range),
            "last_checkpoint_id": self._validate_optional_str(
                manifest["last_checkpoint_id"], field_name="last_checkpoint_id"
            ),
            "status": self._validate_str(manifest["status"], field_name="status"),
            "created_at": self._validate_str(manifest["created_at"], field_name="created_at"),
            "updated_at": self._validate_str(manifest["updated_at"], field_name="updated_at"),
        }

    def _validate_manifest_keys(self, manifest: dict[str, object]) -> None:
        unknown_fields = sorted(set(manifest) - self._MANIFEST_FIELDS)
        if unknown_fields:
            raise ValueError(f"Unknown continue session manifest fields: {', '.join(unknown_fields)}")

        missing_fields = sorted(self._MANIFEST_FIELDS - set(manifest))
        if missing_fields:
            raise ValueError(f"Missing continue session manifest fields: {', '.join(missing_fields)}")

    @staticmethod
    def _validate_int(value: object, *, field_name: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{field_name} must be an integer")
        return value

    @staticmethod
    def _validate_str(value: object, *, field_name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string")
        return value

    @staticmethod
    def _validate_optional_str(value: object, *, field_name: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string or null")
        return value

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
