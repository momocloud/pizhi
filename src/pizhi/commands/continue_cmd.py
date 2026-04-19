from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.checkpoint_store import CheckpointRecord
from pizhi.services.continue_execution import resume_continue_execution
from pizhi.services.continue_execution import start_continue_execution
from pizhi.services.continue_service import ContinueService
from pizhi.services.continue_session_store import ContinueSessionRecord
from pizhi.services.continue_session_store import ContinueSessionStore


def run_continue(args: argparse.Namespace) -> int:
    command = getattr(args, "continue_command", None) or "run"
    if command == "sessions":
        return _run_sessions()
    if command == "resume":
        return _run_resume(args)
    return _run_run(args)


def _run_run(args: argparse.Namespace) -> int:
    if args.execute:
        if args.outline_response_file or args.chapter_responses_dir:
            print(
                "error: --execute cannot be used with --outline-response-file or --chapter-responses-dir",
                file=sys.stderr,
            )
            return 2
        return _run_execute(args)
    return _run_prompt_only(args)


def _run_execute(args: argparse.Namespace) -> int:
    try:
        result = start_continue_execution(
            Path.cwd(),
            count=args.count,
            direction=args.direction or "",
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_session(result.session)
    if result.checkpoint is not None:
        _print_checkpoint(result.checkpoint)
    return 0


def _run_prompt_only(args: argparse.Namespace) -> int:
    try:
        result = ContinueService(Path.cwd()).continue_project(
            count=args.count,
            outline_response_file=Path(args.outline_response_file) if args.outline_response_file else None,
            chapter_responses_dir=Path(args.chapter_responses_dir) if args.chapter_responses_dir else None,
            direction=args.direction or "",
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    start, end = result.chapter_range
    print(f"Continued chapters ch{start:03d}-ch{end:03d}")
    return 0


def _run_sessions() -> int:
    try:
        records = _load_continue_sessions(Path.cwd())
    except Exception as exc:
        print(f"error: unable to list continue sessions: {exc}", file=sys.stderr)
        return 1

    for record in records:
        _print_session(record)
    return 0


def _run_resume(args: argparse.Namespace) -> int:
    try:
        result = resume_continue_execution(Path.cwd(), args.session_id)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_session(result.session)
    if result.checkpoint is not None:
        _print_checkpoint(result.checkpoint)
    return 0


def _load_continue_sessions(project_root: Path) -> list[ContinueSessionRecord]:
    paths = project_paths(project_root)
    if not paths.continue_sessions_dir.exists():
        return []

    store = ContinueSessionStore(paths.continue_sessions_dir)
    return [
        store.load(entry.name)
        for entry in sorted(paths.continue_sessions_dir.iterdir())
        if entry.is_dir()
    ]


def _print_session(record: ContinueSessionRecord) -> None:
    checkpoint_id = record.last_checkpoint_id or ""
    print(
        f"session_id={record.session_id} "
        f"checkpoint_id={checkpoint_id} "
        f"stage={record.current_stage} "
        f"status={record.status}"
    )


def _print_checkpoint(record: CheckpointRecord) -> None:
    print(
        f"checkpoint_id={record.checkpoint_id} "
        f"session_id={record.session_id} "
        f"stage={record.stage} "
        f"status={record.status}"
    )
