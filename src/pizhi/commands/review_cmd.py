from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.consistency.structural import run_structural_review


def run_review(args: argparse.Namespace) -> int:
    report = run_structural_review(Path.cwd(), chapter_number=args.chapter, full=args.full)
    print(f"Issues found: {len(report.issues)}")
    return 0
