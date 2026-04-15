from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.compiler import compile_manuscript


def run_compile(args: argparse.Namespace) -> int:
    del args
    written = compile_manuscript(Path.cwd())
    for path in written:
        print(f"Wrote {path.name}")
    return 0
