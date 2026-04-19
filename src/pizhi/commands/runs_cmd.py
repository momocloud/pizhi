from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.run_store import RunStore


def run_runs(args: argparse.Namespace) -> int:
    del args
    store = RunStore(project_paths(Path.cwd()).runs_dir)
    try:
        records = store.list_runs()
    except Exception as exc:
        print(f"error: unable to list runs: {exc}", file=sys.stderr)
        return 1

    for record in records:
        print(f"{record.run_id}  {record.command}  {record.target}  {record.status}  {record.created_at}")
    return 0
