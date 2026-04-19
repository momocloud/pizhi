from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
import re
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.apply_service import apply_run
from pizhi.services.checkpoint_store import CheckpointStore
from pizhi.services.checkpoint_store import CheckpointRecord
from pizhi.services.continue_session_store import ContinueSessionStore
from pizhi.services.continue_session_store import ContinueSessionRecord
from pizhi.services.run_store import RunRecord
from pizhi.services.run_store import RunStore


@dataclass(frozen=True, slots=True)
class CheckpointApplyResult:
    checkpoint: CheckpointRecord
    session: ContinueSessionRecord


def apply_checkpoint(project_root: Path, checkpoint_id: str) -> CheckpointApplyResult:
    paths = project_paths(project_root)
    checkpoint_store = CheckpointStore(paths.checkpoints_dir)
    session_store = ContinueSessionStore(paths.continue_sessions_dir)

    checkpoint = checkpoint_store.load(checkpoint_id)
    if checkpoint.status != "generated":
        raise ValueError(f"checkpoint {checkpoint_id} status is {checkpoint.status}")

    ordered_run_ids = _ordered_run_ids(paths.runs_dir, checkpoint.run_ids)

    try:
        for run_id in ordered_run_ids:
            apply_run(project_root, run_id)
    except Exception:
        checkpoint_store.update(checkpoint_id, status="failed")
        session_store.update(checkpoint.session_id, status="blocked")
        raise

    applied_checkpoint = checkpoint_store.update(
        checkpoint_id,
        status="applied",
        applied_at=_created_at(),
    )
    ready_session = session_store.update(checkpoint.session_id, status="ready_to_resume")
    return CheckpointApplyResult(checkpoint=applied_checkpoint, session=ready_session)


def _ordered_run_ids(runs_dir: Path, run_ids: tuple[str, ...]) -> list[str]:
    run_store = RunStore(runs_dir)
    run_records = [run_store.load(run_id) for run_id in run_ids]
    return [record.run_id for record in sorted(run_records, key=_run_sort_key)]


def _run_sort_key(record: RunRecord) -> tuple[int, int, str]:
    chapter_number, target_number = _parse_run_target(record.target)
    return (chapter_number, target_number, record.run_id)


def _parse_run_target(target: str) -> tuple[int, int]:
    match = re.fullmatch(r"ch(?P<start>\d{3})(?:-ch(?P<end>\d{3}))?", target)
    if match is None:
        raise ValueError(f"unsupported run target: {target}")
    start = int(match.group("start"))
    end = int(match.group("end") or match.group("start"))
    return (start, end)


def _created_at() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
