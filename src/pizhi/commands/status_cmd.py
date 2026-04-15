from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.status_report import STATUS_ORDER
from pizhi.services.status_report import build_status_report


def run_status(args: argparse.Namespace) -> int:
    del args
    report = build_status_report(Path.cwd())
    latest = "none" if report.latest_chapter is None else f"ch{report.latest_chapter:03d}"

    print(f"Project: {report.project_name}")
    print(f"Total planned chapters: {report.total_planned}")
    print(f"Chapters per volume: {report.per_volume}")
    print(f"Latest chapter: {latest}")
    print(f"Next chapter: ch{report.next_chapter:03d}")
    print(f"Compiled volumes: {report.compiled_volumes}")
    print("Chapter counts:")
    for status in STATUS_ORDER:
        print(f"  {status}: {report.chapter_counts.get(status, 0)}")
    return 0
