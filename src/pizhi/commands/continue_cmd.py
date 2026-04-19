from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pizhi.adapters.base import PromptRequest
from pizhi.adapters.prompt_only import PromptOnlyAdapter
from pizhi.commands.checkpoint_cmd import create_continue_checkpoint
from pizhi.commands.checkpoint_cmd import create_continue_session
from pizhi.commands.checkpoint_cmd import list_continue_sessions
from pizhi.commands.checkpoint_cmd import resume_continue_execution
from pizhi.services.continue_service import ContinueService
from pizhi.services.provider_execution import execute_prompt_request


def run_continue(args: argparse.Namespace) -> int:
    command = getattr(args, "continue_command", "run")
    if command == "sessions":
        return _run_sessions()
    if command == "resume":
        return _run_resume(args)
    return _run_run(args)


def _run_run(args: argparse.Namespace) -> int:
    project_root = Path.cwd()
    service = ContinueService(project_root)
    if args.execute and (args.outline_response_file or args.chapter_responses_dir):
        print(
            "error: --execute cannot be used with --outline-response-file or --chapter-responses-dir",
            file=sys.stderr,
        )
        return 2

    if args.execute:
        try:
            chapter_range = service._determine_chapter_range(args.count)
            request = _build_continue_prompt_request(project_root, chapter_range, direction=args.direction or "")
            prompt_artifact = PromptOnlyAdapter(project_root).prepare(request)
            execution = execute_prompt_request(
                project_root,
                request,
                target=f"continue-ch{chapter_range[0]:03d}-ch{chapter_range[1]:03d}",
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print(f"Prepared prompt packet: {prompt_artifact.prompt_path.name}")
        print(f"Run ID: {execution.run_id}")
        if execution.status != "succeeded":
            error_text = execution.record.error_path.read_text(encoding="utf-8").strip()
            print(f"error: {error_text}", file=sys.stderr)
            return 1

        checkpoint_id = f"checkpoint-{execution.run_id}"
        session = create_continue_session(
            project_root,
            checkpoint_id=checkpoint_id,
            chapter_range=chapter_range,
            count=args.count,
            direction=args.direction or "",
            run_id=execution.run_id,
            prompt_packet_id=prompt_artifact.packet_id,
        )
        checkpoint = create_continue_checkpoint(
            project_root,
            checkpoint_id=checkpoint_id,
            session_id=session.session_id,
            chapter_range=chapter_range,
            run_id=execution.run_id,
            prompt_packet_id=prompt_artifact.packet_id,
            normalized_text=execution.record.normalized_path.read_text(encoding="utf-8"),
        )
        print(f"Session ID: {session.session_id}")
        print(f"Stage: {session.stage}")
        print(f"Status: {session.status}")
        print(f"Checkpoint ID: {checkpoint.checkpoint_id}")
        print(f"Checkpoint Stage: {checkpoint.stage}")
        print(f"Checkpoint Status: {checkpoint.status}")
        return 0

    result = service.continue_project(
        count=args.count,
        outline_response_file=Path(args.outline_response_file) if args.outline_response_file else None,
        chapter_responses_dir=Path(args.chapter_responses_dir) if args.chapter_responses_dir else None,
        direction=args.direction or "",
    )
    start, end = result.chapter_range
    print(f"Continued chapters ch{start:03d}-ch{end:03d}")
    return 0


def _run_sessions() -> int:
    records = list_continue_sessions(Path.cwd())
    for record in records:
        print(f"Session ID: {record.session_id}")
        print(f"Stage: {record.stage}")
        print(f"Status: {record.status}")
        print(f"Checkpoint ID: {record.checkpoint_id}")
        print(f"Created At: {record.created_at}")
        print("")
    return 0


def _run_resume(args: argparse.Namespace) -> int:
    try:
        record = resume_continue_execution(Path.cwd(), args.session_id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Session ID: {record.session_id}")
    print(f"Stage: {record.stage}")
    print(f"Status: {record.status}")
    print(f"Checkpoint ID: {record.checkpoint_id}")
    return 0


def _build_continue_prompt_request(project_root: Path, chapter_range: tuple[int, int], *, direction: str) -> PromptRequest:
    start, end = chapter_range
    direction_text = direction or "Continue the established arc."
    return PromptRequest(
        command_name="continue",
        prompt_text=(
            "# Continue Session Request\n\n"
            f"Count: {end - start + 1}\n"
            f"Chapter Range: ch{start:03d}-ch{end:03d}\n\n"
            f"Direction: {direction_text}\n\n"
            "Return a concise orchestration packet for outline and chapter continuation."
        ),
        metadata={
            "count": end - start + 1,
            "chapter_range": [start, end],
            "direction": direction,
            "mode": "execute",
        },
        referenced_files=[
            ".pizhi/global/synopsis.md",
            ".pizhi/global/worldview.md",
            ".pizhi/global/rules.md",
            ".pizhi/global/outline_global.md",
            ".pizhi/chapters/index.jsonl",
        ],
    )
