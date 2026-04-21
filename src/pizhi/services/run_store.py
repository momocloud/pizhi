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

    @staticmethod
    def new_run_id() -> str:
        return RunStore._new_run_id()

    def mark_failure(self, run_id: str, *, error_text: str, status: str = "failed") -> RunRecord:
        record = self.load(run_id)
        record.error_path.write_text(error_text, encoding="utf-8", newline="\n")
        manifest_path = record.manifest_path
        manifest_path.write_text(
            json.dumps(
                self._build_manifest(
                    run_id=record.run_id,
                    command=record.command,
                    target=record.target,
                    status=status,
                    created_at=record.created_at,
                    metadata=record.metadata,
                    referenced_files=record.referenced_files,
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return self._record_from_paths(
            run_id=record.run_id,
            run_dir=record.run_dir,
            command=record.command,
            target=record.target,
            status=status,
            created_at=record.created_at,
            metadata=record.metadata,
            referenced_files=record.referenced_files,
        )

    def write_success(
        self,
        *,
        run_id: str | None = None,
        command: str,
        target: str,
        prompt_text: str,
        raw_payload: dict[str, Any],
        normalized_text: str,
        metadata: dict[str, Any],
        referenced_files: list[str] | None = None,
        extra_files: dict[str, str] | None = None,
    ) -> RunRecord:
        run_id = run_id or self._new_run_id()
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
        self._write_extra_files(run_dir, extra_files)
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
        run_id: str | None = None,
        command: str,
        target: str,
        prompt_text: str,
        raw_payload: dict[str, Any] | None = None,
        normalized_text: str | None = None,
        error_text: str,
        status: str = "failed",
        metadata: dict[str, Any],
        referenced_files: list[str] | None = None,
        extra_files: dict[str, str] | None = None,
    ) -> RunRecord:
        run_id = run_id or self._new_run_id()
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        created_at = self._created_at()
        prompt_path = run_dir / "prompt.md"
        manifest_path = run_dir / "manifest.json"
        raw_path = run_dir / "raw.json"
        normalized_path = run_dir / "normalized.md"
        error_path = run_dir / "error.txt"

        prompt_path.write_text(prompt_text, encoding="utf-8", newline="\n")
        if raw_payload is not None:
            raw_path.write_text(
                json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        if normalized_text is not None:
            normalized_path.write_text(normalized_text, encoding="utf-8", newline="\n")
        error_path.write_text(error_text, encoding="utf-8", newline="\n")
        self._write_extra_files(run_dir, extra_files)
        manifest_path.write_text(
            json.dumps(
                self._build_manifest(
                    run_id=run_id,
                    command=command,
                    target=target,
                    status=status,
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
            status=status,
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
            for run_dir in sorted(self.runs_dir.iterdir(), reverse=True)
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
        backend = metadata.get("backend")
        backend_implementation = metadata.get("backend_implementation")
        request_path = metadata.get("request_path")
        task_path = metadata.get("task_path")
        output_path = metadata.get("output_path")
        stdout_path = metadata.get("stdout_path")
        stderr_path = metadata.get("stderr_path")
        return {
            "run_id": run_id,
            "command": command,
            "target": target,
            "status": status,
            "created_at": created_at,
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "backend": backend,
            "backend_implementation": backend_implementation,
            "request_path": request_path,
            "task_path": task_path,
            "output_path": output_path,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "metadata": metadata,
            "referenced_files": referenced_files,
        }

    @staticmethod
    def _write_extra_files(run_dir: Path, extra_files: dict[str, str] | None) -> None:
        if not extra_files:
            return
        for relative_path, content in extra_files.items():
            path = run_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")

    @staticmethod
    def _created_at() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _new_run_id() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"run-{timestamp}-{uuid4().hex[:8]}"
