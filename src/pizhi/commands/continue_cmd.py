from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.continue_service import ContinueService


def run_continue(args: argparse.Namespace) -> int:
    service = ContinueService(Path.cwd())
    result = service.continue_project(
        count=args.count,
        outline_response_file=Path(args.outline_response_file) if args.outline_response_file else None,
        chapter_responses_dir=Path(args.chapter_responses_dir) if args.chapter_responses_dir else None,
        direction=args.direction or "",
    )
    start, end = result.chapter_range
    print(f"Continued chapters ch{start:03d}-ch{end:03d}")
    return 0
