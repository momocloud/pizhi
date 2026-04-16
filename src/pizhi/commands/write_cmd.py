from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.write_service import WriteService


def run_write(args: argparse.Namespace) -> int:
    service = WriteService(Path.cwd())
    response_file = Path(args.response_file) if args.response_file else None
    result = service.write(chapter_number=args.chapter, response_file=response_file)
    print(f"Prepared prompt packet: {result.prompt_artifact.prompt_path.name}")
    return 0
