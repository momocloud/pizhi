from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pizhi.services.outline_service import OutlineService
from pizhi.services.provider_execution import execute_prompt_request


def run_outline_expand(args: argparse.Namespace) -> int:
    service = OutlineService(Path.cwd())
    response_file = Path(args.response_file) if args.response_file else None
    chapter_range = parse_chapter_range(args.chapters)
    if args.execute and response_file is not None:
        print("error: --execute cannot be used with --response-file", file=sys.stderr)
        return 2

    if args.execute:
        try:
            request = service.build_prompt_request(chapter_range, direction=args.direction or "")
            prompt_artifact = service.prepare_prompt(request)
            target = f"ch{chapter_range[0]:03d}-ch{chapter_range[1]:03d}"
            execution = execute_prompt_request(service.project_root, request, target=target)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"Prepared prompt packet: {prompt_artifact.prompt_path.name}")
        print(f"Run ID: {execution.run_id}")
        if execution.status == "provider_failed":
            error_text = execution.record.error_path.read_text(encoding="utf-8").strip()
            print(f"error: {error_text}", file=sys.stderr)
            return 1
        return 0

    result = service.expand(
        chapter_range=chapter_range,
        response_file=response_file,
        direction=args.direction or "",
    )
    print(f"Prepared prompt packet: {result.prompt_artifact.prompt_path.name}")
    return 0


def parse_chapter_range(raw: str) -> tuple[int, int]:
    start_text, end_text = raw.split("-", maxsplit=1)
    start = int(start_text)
    end = int(end_text)
    if start > end:
        raise ValueError("chapter range start must be <= end")
    return start, end
