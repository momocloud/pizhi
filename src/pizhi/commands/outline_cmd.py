from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.outline_service import OutlineService


def run_outline_expand(args: argparse.Namespace) -> int:
    service = OutlineService(Path.cwd())
    response_file = Path(args.response_file) if args.response_file else None
    chapter_range = parse_chapter_range(args.chapters)
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
