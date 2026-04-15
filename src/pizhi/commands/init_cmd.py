from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.project_init import ProjectInitService


def run_init(args: argparse.Namespace) -> int:
    service = ProjectInitService(Path.cwd())
    service.initialize(
        name=args.project_name,
        genre=args.genre,
        total_chapters=args.total_chapters,
        per_volume=args.per_volume,
        pov=args.pov,
    )
    print(f"Initialized Pizhi project in {Path.cwd()}")
    return 0
