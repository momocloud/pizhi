from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    checkpoint_id: str
    checkpoint_dir: Path
    manifest_path: Path
    session_id: str
    stage: str
    chapter_range: tuple[int, int]
    run_ids: tuple[str, ...]
    status: str
    created_at: str
    applied_at: str | None


class CheckpointStore:
    _MANIFEST_FIELDS = frozenset(
        {
            "checkpoint_id",
            "session_id",
            "stage",
            "chapter_range",
            "run_ids",
            "status",
            "created_at",
            "applied_at",
        }
    )
    _UPDATE_FIELDS = frozenset({"status", "applied_at"})

    def __init__(self, checkpoints_dir: Path) -> None:
        self.checkpoints_dir = checkpoints_dir

    def create(
        self,
        *,
        session_id: str,
        stage: str,
        chapter_range: tuple[int, int],
        run_ids: list[str],
        status: str,
        applied_at: str | None = None,
    ) -> CheckpointRecord:
        checkpoint_id = self._new_checkpoint_id()
        checkpoint_dir = self.checkpoints_dir / checkpoint_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        created_at = self._created_at()

        manifest = self._build_manifest(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            stage=stage,
            chapter_range=chapter_range,
            run_ids=run_ids,
            status=status,
            created_at=created_at,
            applied_at=applied_at,
        )
        manifest_path = checkpoint_dir / "manifest.json"
        self._write_manifest(manifest_path, manifest)
        return self._record_from_manifest(checkpoint_dir=checkpoint_dir, manifest=manifest)

    def load(self, checkpoint_id: str) -> CheckpointRecord:
        checkpoint_dir = self.checkpoints_dir / checkpoint_id
        manifest_path = checkpoint_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return self._record_from_manifest(checkpoint_dir=checkpoint_dir, manifest=manifest)

    def update(self, checkpoint_id: str, **changes: object) -> CheckpointRecord:
        record = self.load(checkpoint_id)
        manifest = self._manifest_from_record(record)
        manifest.update(self._normalize_update_changes(changes))
        normalized_manifest = self._normalize_manifest(manifest)
        self._write_manifest(record.manifest_path, normalized_manifest)
        return self._record_from_manifest(checkpoint_dir=record.checkpoint_dir, manifest=normalized_manifest)

    def _record_from_manifest(
        self,
        *,
        checkpoint_dir: Path,
        manifest: dict[str, object],
    ) -> CheckpointRecord:
        normalized_manifest = self._normalize_manifest(manifest)
        return CheckpointRecord(
            checkpoint_id=normalized_manifest["checkpoint_id"],
            checkpoint_dir=checkpoint_dir,
            manifest_path=checkpoint_dir / "manifest.json",
            session_id=normalized_manifest["session_id"],
            stage=normalized_manifest["stage"],
            chapter_range=tuple(normalized_manifest["chapter_range"]),
            run_ids=tuple(normalized_manifest["run_ids"]),
            status=normalized_manifest["status"],
            created_at=normalized_manifest["created_at"],
            applied_at=normalized_manifest["applied_at"],
        )

    def _manifest_from_record(self, record: CheckpointRecord) -> dict[str, object]:
        return {
            "checkpoint_id": record.checkpoint_id,
            "session_id": record.session_id,
            "stage": record.stage,
            "chapter_range": list(record.chapter_range),
            "run_ids": list(record.run_ids),
            "status": record.status,
            "created_at": record.created_at,
            "applied_at": record.applied_at,
        }

    def _build_manifest(
        self,
        *,
        checkpoint_id: str,
        session_id: str,
        stage: str,
        chapter_range: tuple[int, int],
        run_ids: list[str],
        status: str,
        created_at: str,
        applied_at: str | None,
    ) -> dict[str, object]:
        return self._normalize_manifest(
            {
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "stage": stage,
            "chapter_range": chapter_range,
            "run_ids": run_ids,
            "status": status,
            "created_at": created_at,
            "applied_at": applied_at,
        }
        )

    def _normalize_update_changes(self, changes: dict[str, object]) -> dict[str, object]:
        unknown_fields = sorted(set(changes) - self._UPDATE_FIELDS)
        if unknown_fields:
            raise ValueError(f"Unknown update fields: {', '.join(unknown_fields)}")

        normalized_changes: dict[str, object] = {}
        for field_name, value in changes.items():
            if field_name == "status":
                normalized_changes[field_name] = self._validate_str(value, field_name=field_name)
            elif field_name == "applied_at":
                normalized_changes[field_name] = self._validate_optional_str(value, field_name=field_name)
        return normalized_changes

    def _normalize_manifest(self, manifest: dict[str, object]) -> dict[str, object]:
        self._validate_manifest_keys(manifest)
        chapter_range = self._validate_int_pair(manifest["chapter_range"], field_name="chapter_range")
        run_ids = self._validate_run_ids(manifest["run_ids"])
        return {
            "checkpoint_id": self._validate_str(manifest["checkpoint_id"], field_name="checkpoint_id"),
            "session_id": self._validate_str(manifest["session_id"], field_name="session_id"),
            "stage": self._validate_str(manifest["stage"], field_name="stage"),
            "chapter_range": list(chapter_range),
            "run_ids": list(run_ids),
            "status": self._validate_str(manifest["status"], field_name="status"),
            "created_at": self._validate_str(manifest["created_at"], field_name="created_at"),
            "applied_at": self._validate_optional_str(manifest["applied_at"], field_name="applied_at"),
        }

    def _validate_manifest_keys(self, manifest: dict[str, object]) -> None:
        unknown_fields = sorted(set(manifest) - self._MANIFEST_FIELDS)
        if unknown_fields:
            raise ValueError(f"Unknown checkpoint manifest fields: {', '.join(unknown_fields)}")

        missing_fields = sorted(self._MANIFEST_FIELDS - set(manifest))
        if missing_fields:
            raise ValueError(f"Missing checkpoint manifest fields: {', '.join(missing_fields)}")

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
    def _validate_run_ids(value: object) -> tuple[str, ...]:
        if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
            raise ValueError("run_ids must be a sequence of strings")
        if any(not isinstance(run_id, str) for run_id in value):
            raise ValueError("run_ids must be a sequence of strings")
        return tuple(value)

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
    def _new_checkpoint_id() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"checkpoint-{timestamp}-{uuid4().hex[:8]}"
