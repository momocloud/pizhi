from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.checkpoint_apply_service import apply_checkpoint
from pizhi.services.checkpoint_store import CheckpointRecord
from pizhi.services.checkpoint_store import CheckpointStore
from pizhi.services.continue_session_store import ContinueSessionRecord
from pizhi.services.continue_session_store import ContinueSessionStore
from pizhi.services.maintenance import format_maintenance_summary


def run_checkpoint_apply(args: argparse.Namespace) -> int:
    try:
        _preflight_checkpoint_apply(Path.cwd(), checkpoint_id=args.id)
        result = apply_checkpoint(Path.cwd(), args.id)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_checkpoint(result.checkpoint)
    _print_session(result.session)
    for chapter_number, maintenance_result in result.maintenance_results:
        print(f"chapter=ch{chapter_number:03d}")
        print(format_maintenance_summary(maintenance_result), end="")
    return 0


def run_checkpoints(args: argparse.Namespace) -> int:
    try:
        records = _load_checkpoints(Path.cwd(), session_id=args.session_id)
    except Exception as exc:
        print(f"error: unable to list checkpoints: {exc}", file=sys.stderr)
        return 1

    for record in records:
        _print_checkpoint(record)
    return 0


def _load_checkpoints(project_root: Path, *, session_id: str) -> list[CheckpointRecord]:
    paths = project_paths(project_root)
    if not paths.checkpoints_dir.exists():
        return []

    store = CheckpointStore(paths.checkpoints_dir)
    return [
        record
        for record in (
            store.load(entry.name)
            for entry in sorted(paths.checkpoints_dir.iterdir())
            if entry.is_dir()
        )
        if record.session_id == session_id
    ]


def _preflight_checkpoint_apply(project_root: Path, *, checkpoint_id: str) -> None:
    paths = project_paths(project_root)
    checkpoint = CheckpointStore(paths.checkpoints_dir).load(checkpoint_id)
    ContinueSessionStore(paths.continue_sessions_dir).load(checkpoint.session_id)


def _print_checkpoint(record: CheckpointRecord) -> None:
    print(
        f"checkpoint_id={record.checkpoint_id} "
        f"session_id={record.session_id} "
        f"stage={record.stage} "
        f"status={record.status}"
    )


def _print_session(record: ContinueSessionRecord) -> None:
    checkpoint_id = record.last_checkpoint_id or ""
    print(
        f"session_id={record.session_id} "
        f"checkpoint_id={checkpoint_id} "
        f"stage={record.current_stage} "
        f"status={record.status}"
    )
