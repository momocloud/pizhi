from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
import re
import shutil
import tempfile
from pathlib import Path
from contextlib import contextmanager
from contextlib import suppress

from pizhi.core.paths import project_paths
from pizhi.services.apply_service import apply_run
from pizhi.services.checkpoint_store import CheckpointStore
from pizhi.services.checkpoint_store import CheckpointRecord
from pizhi.services.continue_session_store import ContinueSessionStore
from pizhi.services.continue_session_store import ContinueSessionRecord
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.run_store import RunRecord
from pizhi.services.run_store import RunStore


@dataclass(frozen=True, slots=True)
class CheckpointApplyResult:
    checkpoint: CheckpointRecord
    session: ContinueSessionRecord
    maintenance_results: list[tuple[int, MaintenanceResult | None]]


def apply_checkpoint(project_root: Path, checkpoint_id: str) -> CheckpointApplyResult:
    paths = project_paths(project_root)
    checkpoint_store = CheckpointStore(paths.checkpoints_dir)
    session_store = ContinueSessionStore(paths.continue_sessions_dir)

    checkpoint = checkpoint_store.load(checkpoint_id)
    session = session_store.load(checkpoint.session_id)
    if checkpoint.status != "generated":
        raise ValueError(f"checkpoint {checkpoint_id} status is {checkpoint.status}")

    phase = "apply"
    try:
        with _project_state_backup(
            paths,
            extra_targets=[checkpoint.manifest_path, session.manifest_path],
        ):
            ordered_run_records = _ordered_run_records(paths.runs_dir, checkpoint.run_ids)
            maintenance_results: list[tuple[int, MaintenanceResult | None]] = []
            for run_record in ordered_run_records:
                apply_result = apply_run(project_root, run_record.run_id)
                if run_record.command == "write":
                    chapter_number, _ = _parse_run_target(run_record.target)
                    maintenance_results.append((chapter_number, apply_result.maintenance_result))

            phase = "finalize"
            applied_checkpoint = checkpoint_store.update(
                checkpoint_id,
                status="applied",
                applied_at=_created_at(),
            )
            ready_session = session_store.update(checkpoint.session_id, status="ready_to_resume")
            return CheckpointApplyResult(
                checkpoint=applied_checkpoint,
                session=ready_session,
                maintenance_results=maintenance_results,
            )
    except Exception:
        if phase == "apply":
            checkpoint_store.update(checkpoint_id, status="failed")
            session_store.update(checkpoint.session_id, status="blocked")
        raise


def _ordered_run_records(runs_dir: Path, run_ids: tuple[str, ...]) -> list[RunRecord]:
    run_store = RunStore(runs_dir)
    run_records = [run_store.load(run_id) for run_id in run_ids]
    return sorted(run_records, key=_run_sort_key)


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


@contextmanager
def _project_state_backup(paths, *, extra_targets: list[Path] | None = None):
    backup_root = Path(tempfile.mkdtemp(prefix="pizhi-checkpoint-apply-"))
    targets = [
        paths.global_dir,
        paths.chapters_dir,
        paths.archive_dir,
        paths.last_session_file,
        paths.cache_dir / "synopsis_review.pending",
        paths.cache_dir / "synopsis_review.md",
    ]
    if extra_targets is not None:
        targets.extend(extra_targets)
    snapshots: list[tuple[Path, Path, bool, bool]] = []
    try:
        for target in targets:
            snapshots.append(_snapshot_target(backup_root, target))
        yield
    except Exception:
        for target, backup_path, existed, is_dir in reversed(snapshots):
            _restore_target(target, backup_path, existed=existed, is_dir=is_dir)
        raise
    finally:
        shutil.rmtree(backup_root, ignore_errors=True)


def _snapshot_target(backup_root: Path, target: Path) -> tuple[Path, Path, bool, bool]:
    exists = target.exists()
    is_dir = target.is_dir() if exists else False
    backup_path = backup_root / _backup_name(target)
    if exists:
        if is_dir:
            shutil.copytree(target, backup_path)
        else:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_path)
    return (target, backup_path, exists, is_dir)


def _restore_target(target: Path, backup_path: Path, *, existed: bool, is_dir: bool) -> None:
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

    if not existed:
        return

    if is_dir:
        shutil.copytree(backup_path, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, target)


def _backup_name(target: Path) -> str:
    return "__".join(target.parts[-4:]).replace(":", "_")
