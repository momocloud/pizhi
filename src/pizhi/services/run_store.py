from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    run_dir: Path
    manifest_path: Path
    prompt_path: Path
    raw_path: Path
    normalized_path: Path
    error_path: Path
    command: str
    target: str
    status: str
    created_at: str
    metadata: dict[str, Any]
    referenced_files: list[str]


class RunStore:
    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir

    def write_success(
        self,
        *,
        command: str,
        target: str,
        prompt_text: str,
        raw_payload: dict[str, Any],
        normalized_text: str,
        metadata: dict[str, Any],
        referenced_files: list[str] | None = None,
    ) -> RunRecord:
        run_id = self._new_run_id()
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        created_at = self._created_at()
        prompt_path = run_dir / "prompt.md"
        manifest_path = run_dir / "manifest.json"
        raw_path = run_dir / "raw.json"
        normalized_path = run_dir / "normalized.md"
        error_path = run_dir / "error.txt"

        prompt_path.write_text(prompt_text, encoding="utf-8", newline="\n")
        raw_path.write_text(
            json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        normalized_path.write_text(normalized_text, encoding="utf-8", newline="\n")
        manifest_path.write_text(
            json.dumps(
                self._build_manifest(
                    run_id=run_id,
                    command=command,
                    target=target,
                    status="succeeded",
                    created_at=created_at,
                    metadata=metadata,
                    referenced_files=referenced_files or [],
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

        return self._record_from_paths(
            run_id=run_id,
            run_dir=run_dir,
            command=command,
            target=target,
            status="succeeded",
            created_at=created_at,
            metadata=metadata,
            referenced_files=referenced_files or [],
        )

    def write_failure(
        self,
        *,
        command: str,
        target: str,
        prompt_text: str,
        error_text: str,
        metadata: dict[str, Any],
        referenced_files: list[str] | None = None,
    ) -> RunRecord:
        run_id = self._new_run_id()
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        created_at = self._created_at()
        prompt_path = run_dir / "prompt.md"
        manifest_path = run_dir / "manifest.json"
        raw_path = run_dir / "raw.json"
        normalized_path = run_dir / "normalized.md"
        error_path = run_dir / "error.txt"

        prompt_path.write_text(prompt_text, encoding="utf-8", newline="\n")
        error_path.write_text(error_text, encoding="utf-8", newline="\n")
        manifest_path.write_text(
            json.dumps(
                self._build_manifest(
                    run_id=run_id,
                    command=command,
                    target=target,
                    status="failed",
                    created_at=created_at,
                    metadata=metadata,
                    referenced_files=referenced_files or [],
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

        return self._record_from_paths(
            run_id=run_id,
            run_dir=run_dir,
            command=command,
            target=target,
            status="failed",
            created_at=created_at,
            metadata=metadata,
            referenced_files=referenced_files or [],
        )

    def load(self, run_id: str) -> RunRecord:
        run_dir = self.runs_dir / run_id
        manifest_path = run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return self._record_from_manifest(run_dir=run_dir, manifest=manifest)

    def list_runs(self) -> list[RunRecord]:
        if not self.runs_dir.exists():
            return []

        records = [
            self.load(run_dir.name)
            for run_dir in sorted(self.runs_dir.iterdir())
            if run_dir.is_dir() and (run_dir / "manifest.json").exists()
        ]
        return records

    def _record_from_manifest(self, *, run_dir: Path, manifest: dict[str, Any]) -> RunRecord:
        return RunRecord(
            run_id=manifest["run_id"],
            run_dir=run_dir,
            manifest_path=run_dir / "manifest.json",
            prompt_path=run_dir / "prompt.md",
            raw_path=run_dir / "raw.json",
            normalized_path=run_dir / "normalized.md",
            error_path=run_dir / "error.txt",
            command=manifest["command"],
            target=manifest["target"],
            status=manifest["status"],
            created_at=manifest["created_at"],
            metadata=dict(manifest["metadata"]),
            referenced_files=list(manifest.get("referenced_files", [])),
        )

    def _record_from_paths(
        self,
        *,
        run_id: str,
        run_dir: Path,
        command: str,
        target: str,
        status: str,
        created_at: str,
        metadata: dict[str, Any],
        referenced_files: list[str],
    ) -> RunRecord:
        return RunRecord(
            run_id=run_id,
            run_dir=run_dir,
            manifest_path=run_dir / "manifest.json",
            prompt_path=run_dir / "prompt.md",
            raw_path=run_dir / "raw.json",
            normalized_path=run_dir / "normalized.md",
            error_path=run_dir / "error.txt",
            command=command,
            target=target,
            status=status,
            created_at=created_at,
            metadata=dict(metadata),
            referenced_files=list(referenced_files),
        )

    def _build_manifest(
        self,
        *,
        run_id: str,
        command: str,
        target: str,
        status: str,
        created_at: str,
        metadata: dict[str, Any],
        referenced_files: list[str],
    ) -> dict[str, Any]:
        provider = metadata.get("provider")
        model = metadata.get("model")
        base_url = metadata.get("base_url")
        return {
            "run_id": run_id,
            "command": command,
            "target": target,
            "status": status,
            "created_at": created_at,
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "metadata": metadata,
            "referenced_files": referenced_files,
        }

    @staticmethod
    def _created_at() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _new_run_id() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"run-{timestamp}-{uuid4().hex[:8]}"
