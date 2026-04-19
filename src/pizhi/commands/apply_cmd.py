from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pizhi.services.apply_service import apply_run


def run_apply(args: argparse.Namespace) -> int:
    try:
        result = apply_run(Path.cwd(), args.run_id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Applied run: {result.run_id} {result.command} {result.target}")
    return 0
