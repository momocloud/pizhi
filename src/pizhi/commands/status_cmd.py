from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.status_report import STATUS_ORDER
from pizhi.services.status_report import build_status_report


def run_status(args: argparse.Namespace) -> int:
    del args
    report = build_status_report(Path.cwd())
    latest = "none" if report.latest_chapter is None else f"ch{report.latest_chapter:03d}"

    print("Project:")
    print(f"  Name: {report.project_name}")
    print(f"  Total planned chapters: {report.total_planned}")
    print(f"  Chapters per volume: {report.per_volume}")
    print(f"  Latest chapter: {latest}")
    print(f"  Next chapter: ch{report.next_chapter:03d}")
    print(f"  Compiled volumes: {report.compiled_volumes}")
    print("  Chapter counts:")
    for status in STATUS_ORDER:
        print(f"    {status}: {report.chapter_counts.get(status, 0)}")

    print("Recent chapters:")
    if report.recent_chapters:
        for chapter in report.recent_chapters[:5]:
            title = chapter.title or "(untitled)"
            print(f"  ch{chapter.number:03d} [{chapter.status}] {title}")
    else:
        print("  none")

    print("Pending chapters:")
    _print_pending_queue("outlined -> drafted", report.pending_chapters["outlined"])
    _print_pending_queue("drafted -> reviewed", report.pending_chapters["drafted"])
    _print_pending_queue("reviewed -> compiled", report.pending_chapters["reviewed"])

    print("Foreshadowing:")
    print(f"  Active: {report.active_foreshadowing_count}")
    print(f"  Active windows: {_format_foreshadowing_entries(report.active_foreshadowing)}")
    print(f"  Near payoff: {_format_foreshadowing_entries(report.near_payoff_foreshadowing)}")
    print(f"  Overdue: {_format_foreshadowing_entries(report.overdue_foreshadowing)}")
    return 0


def _print_pending_queue(label: str, chapters: list) -> None:
    if chapters:
        chapter_list = ", ".join(f"ch{chapter.number:03d}" for chapter in chapters)
    else:
        chapter_list = "none"
    print(f"  {label}: {chapter_list}")


def _format_foreshadowing_entries(entries: list) -> str:
    if not entries:
        return "none"

    formatted: list[str] = []
    for entry in entries:
        if entry.planned_payoff is None:
            formatted.append(entry.entry_id)
            continue
        payoff = _format_payoff_window(entry)
        formatted.append(f"{entry.entry_id} ({payoff})")
    return ", ".join(formatted)


def _format_payoff_window(entry) -> str:
    planned_payoff = entry.planned_payoff
    if planned_payoff is None:
        return ""
    start = f"ch{planned_payoff.start_chapter:03d}"
    if planned_payoff.open_ended:
        return f"{start}+"
    end = planned_payoff.end_chapter or planned_payoff.start_chapter
    if end == planned_payoff.start_chapter:
        return start
    return f"{start}-ch{end:03d}"
