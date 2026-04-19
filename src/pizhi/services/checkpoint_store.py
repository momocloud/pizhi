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
        normalized_chapter_range = self._validate_int_pair(chapter_range, field_name="chapter_range")
        normalized_run_ids = self._validate_run_ids(run_ids)
        checkpoint_id = self._new_checkpoint_id()
        checkpoint_dir = self.checkpoints_dir / checkpoint_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        created_at = self._created_at()

        manifest = self._build_manifest(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            stage=stage,
            chapter_range=normalized_chapter_range,
            run_ids=normalized_run_ids,
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
        if "chapter_range" in changes:
            changes = {
                **changes,
                "chapter_range": list(
                    self._validate_int_pair(changes["chapter_range"], field_name="chapter_range")
                ),
            }
        if "run_ids" in changes:
            changes = {
                **changes,
                "run_ids": list(self._validate_run_ids(changes["run_ids"])),
            }
        manifest.update(changes)
        self._write_manifest(record.manifest_path, manifest)
        return self._record_from_manifest(checkpoint_dir=record.checkpoint_dir, manifest=manifest)

    def _record_from_manifest(
        self,
        *,
        checkpoint_dir: Path,
        manifest: dict[str, object],
    ) -> CheckpointRecord:
        chapter_range = self._validate_int_pair(manifest.get("chapter_range"), field_name="chapter_range")
        run_ids = self._validate_run_ids(manifest.get("run_ids"))
        return CheckpointRecord(
            checkpoint_id=str(manifest["checkpoint_id"]),
            checkpoint_dir=checkpoint_dir,
            manifest_path=checkpoint_dir / "manifest.json",
            session_id=str(manifest["session_id"]),
            stage=str(manifest["stage"]),
            chapter_range=chapter_range,
            run_ids=run_ids,
            status=str(manifest["status"]),
            created_at=str(manifest["created_at"]),
            applied_at=manifest.get("applied_at") or None,
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
        normalized_chapter_range = self._validate_int_pair(chapter_range, field_name="chapter_range")
        normalized_run_ids = self._validate_run_ids(run_ids)
        return {
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "stage": stage,
            "chapter_range": list(normalized_chapter_range),
            "run_ids": list(normalized_run_ids),
            "status": status,
            "created_at": created_at,
            "applied_at": applied_at,
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
