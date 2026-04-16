from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.brainstorm_service import BrainstormService


def run_brainstorm(args: argparse.Namespace) -> int:
    service = BrainstormService(Path.cwd())
    response_file = Path(args.response_file) if args.response_file else None
    result = service.run(response_file=response_file)
    print(f"Prepared prompt packet: {result.prompt_artifact.prompt_path.name}")
    return 0
