from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.consistency.structural import format_structural_report
from pizhi.services.consistency.structural import run_structural_review


def run_review(args: argparse.Namespace) -> int:
    project_root = Path.cwd()
    report = run_structural_review(project_root, chapter_number=args.chapter, full=args.full)
    print(f"Chapters reviewed: {report.chapters_reviewed}")
    print(f"Chapters with issues: {report.chapters_with_issues}")
    print(f"Chapter issues: {report.total_chapter_issues}")
    print(f"Global issues: {len(report.global_issues)}")

    if args.full:
        report_path = project_paths(project_root).cache_dir / "review_full.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(format_structural_report(report), encoding="utf-8", newline="\n")
        print(f"Full report: {report_path}")

    return 0
