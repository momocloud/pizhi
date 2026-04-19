from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.brainstorm_service import BrainstormService
from pizhi.services.outline_service import OutlineService
from pizhi.services.run_store import RunStore
from pizhi.services.write_service import WriteService


@dataclass(frozen=True, slots=True)
class ApplyResult:
    run_id: str
    command: str
    target: str
    status: str


def apply_run(project_root: Path, run_id: str) -> ApplyResult:
    record = RunStore(project_paths(project_root).runs_dir).load(run_id)
    if record.status != "succeeded":
        raise ValueError(f"run {run_id} status is {record.status}")
    if not record.normalized_path.exists():
        raise ValueError(f"run {run_id} is missing normalized.md")

    normalized_text = record.normalized_path.read_text(encoding="utf-8")
    if record.command == "brainstorm":
        BrainstormService(project_root).apply_response(normalized_text)
    elif record.command == "outline-expand":
        OutlineService(project_root).apply_response(normalized_text)
    elif record.command == "write":
        chapter_number = int(record.metadata["chapter"])
        WriteService(project_root).apply_response(chapter_number, normalized_text)
    else:
        raise ValueError(f"unsupported run command: {record.command}")

    return ApplyResult(
        run_id=record.run_id,
        command=record.command,
        target=record.target,
        status=record.status,
    )
