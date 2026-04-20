from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.brainstorm_service import BrainstormService
from pizhi.services.outline_service import OutlineService
from pizhi.services.run_store import RunStore
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.write_service import WriteService


@dataclass(frozen=True, slots=True)
class ApplyResult:
    run_id: str
    command: str
    target: str
    status: str
    maintenance_result: MaintenanceResult | None


def apply_run(project_root: Path, run_id: str) -> ApplyResult:
    runs_dir = project_paths(project_root).runs_dir
    run_dir = runs_dir / run_id
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"run {run_id} does not exist")

    try:
        record = RunStore(runs_dir).load(run_id)
    except Exception as exc:
        raise ValueError(f"run {run_id} has invalid manifest: {exc}") from None

    if record.status != "succeeded":
        raise ValueError(f"run {run_id} status is {record.status}")
    if not record.normalized_path.exists():
        raise ValueError(f"run {run_id} is missing normalized.md")

    try:
        normalized_text = record.normalized_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"run {run_id} has unreadable normalized.md: {exc}") from None

    maintenance_result: MaintenanceResult | None = None
    if record.command == "brainstorm":
        BrainstormService(project_root).apply_response(normalized_text)
    elif record.command == "outline-expand":
        OutlineService(project_root).apply_response(normalized_text)
    elif record.command == "write":
        chapter_number = _load_chapter_number(record.metadata, run_id)
        write_result = WriteService(project_root).apply_response(chapter_number, normalized_text)
        maintenance_result = write_result.maintenance_result
    else:
        raise ValueError(f"unsupported run command: {record.command}")

    return ApplyResult(
        run_id=record.run_id,
        command=record.command,
        target=record.target,
        status=record.status,
        maintenance_result=maintenance_result,
    )


def _load_chapter_number(metadata: dict[str, object], run_id: str) -> int:
    chapter = metadata.get("chapter")
    try:
        return int(chapter)
    except (TypeError, ValueError):
        raise ValueError(f"run {run_id} has invalid chapter metadata") from None
