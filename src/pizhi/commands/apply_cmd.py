from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pizhi.services.apply_service import apply_run
from pizhi.services.maintenance import format_maintenance_summary


def run_apply(args: argparse.Namespace) -> int:
    try:
        result = apply_run(Path.cwd(), args.run_id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Applied run: {result.run_id} {result.command} {result.target}")
    if result.maintenance_result is not None:
        print(format_maintenance_summary(result.maintenance_result), end="")
    return 0
