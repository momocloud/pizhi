from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pizhi.services.compiler import CompileTarget
from pizhi.services.compiler import compile_manuscript


def run_compile(args: argparse.Namespace) -> int:
    try:
        written = compile_manuscript(Path.cwd(), target=_compile_target_from_args(args))
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for path in written:
        print(f"Wrote {path.name}")
    return 0


def _compile_target_from_args(args: argparse.Namespace) -> CompileTarget:
    if getattr(args, "volume", None) is not None:
        return CompileTarget(volume=args.volume)
    if getattr(args, "chapter", None) is not None:
        return CompileTarget(chapter=args.chapter)
    if getattr(args, "chapters", None):
        if "-" not in args.chapters:
            raise ValueError("compile chapter range must look like A-B")
        start_text, end_text = args.chapters.split("-", 1)
        try:
            start = int(start_text)
            end = int(end_text)
        except ValueError as exc:
            raise ValueError(f"invalid chapter range: {args.chapters}") from exc
        return CompileTarget(chapter_start=start, chapter_end=end)
    raise ValueError("compile target is required")
