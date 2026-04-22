from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from string import Template
import subprocess


@dataclass(frozen=True, slots=True)
class StageConfig:
    slug: str
    target_chapters: int
    report_path: Path


@dataclass(frozen=True, slots=True)
class StageExecutionResult:
    stage_name: str
    project_root: Path
    command_log: list[str]
    artifact_index: dict[str, list[str]]
    outcome_summary: str
    claude_stdout: str
    claude_stderr: str
    returncode: int


_STAGE_CONFIGS = {
    "stage1": {
        "target_chapters": 3,
        "report_stem": "e2e-stage-1-smoke.md",
    },
    "stage2": {
        "target_chapters": 10,
        "report_stem": "e2e-stage-2-endurance.md",
    },
    "stage3": {
        "target_chapters": 30,
        "report_stem": "e2e-stage-3-full-run.md",
    },
}

_CLAUDE_STAGE_PROMPT_TEMPLATE_PATH = Path(__file__).with_name("templates") / "claude_stage_prompt.md"


def build_validation_root_name(timestamp: str) -> str:
    sanitized_timestamp = re.sub(r"[^0-9A-Za-z]+", "-", timestamp).strip("-")
    return f"pizhi-e2e-claude-opencode-{sanitized_timestamp}"


def build_validation_root_path(timestamp: str, base_dir: Path | None = None) -> Path:
    root_dir = Path("tmp") if base_dir is None else Path(base_dir)
    return root_dir / build_validation_root_name(timestamp)


def build_stage_report_path(
    stage_slug: str,
    report_date: str,
    docs_dir: Path | None = None,
) -> Path:
    docs_root = Path("docs") / "verification" if docs_dir is None else Path(docs_dir)
    return docs_root / f"{report_date}-{_stage_config(stage_slug)['report_stem']}"


def build_stage_config(
    stage_slug: str,
    report_date: str,
    docs_dir: Path | None = None,
) -> StageConfig:
    stage = _stage_config(stage_slug)
    return StageConfig(
        slug=stage_slug,
        target_chapters=stage["target_chapters"],
        report_path=build_stage_report_path(
            stage_slug,
            report_date=report_date,
            docs_dir=docs_dir,
        ),
    )


def render_claude_stage_prompt(
    *,
    stage_slug: str,
    project_root: str | Path,
    repo_root: str | Path,
    target_chapters: int,
    genre: str,
) -> str:
    template = Template(_load_claude_stage_prompt_template())
    return template.substitute(
        stage_slug=stage_slug,
        project_root=Path(project_root).as_posix(),
        repo_root=Path(repo_root).as_posix(),
        target_chapters=target_chapters,
        genre=genre,
    )


def collect_stage_artifacts(project_root: str | Path) -> dict[str, list[str]]:
    root = Path(project_root).resolve()
    cache_root = root / ".pizhi" / "cache"
    return {
        "runs": _collect_artifact_entries(cache_root / "runs"),
        "sessions": _collect_artifact_entries(cache_root / "continue_sessions"),
        "checkpoints": _collect_artifact_entries(cache_root / "checkpoints"),
        "reports": _collect_artifact_entries(cache_root, filename="review_full.md"),
        "manuscript": _collect_artifact_entries(root / "manuscript"),
    }


def invoke_claude_stage(
    *,
    stage_slug: str,
    project_root: str | Path,
    repo_root: str | Path,
    genre: str,
    command_log: list[str] | None = None,
) -> StageExecutionResult:
    root = Path(project_root).resolve()
    stage_config = build_stage_config(stage_slug, report_date=_current_report_date())
    prompt = render_claude_stage_prompt(
        stage_slug=stage_slug,
        project_root=root,
        repo_root=repo_root,
        target_chapters=stage_config.target_chapters,
        genre=genre,
    )
    commands = [] if command_log is None else list(command_log)
    commands.append("claude -p <rendered prompt>")
    completed = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        check=False,
        cwd=root,
    )
    artifact_index = collect_stage_artifacts(root)
    return StageExecutionResult(
        stage_name=stage_config.slug.replace("stage", "Stage "),
        project_root=root,
        command_log=commands,
        artifact_index=artifact_index,
        outcome_summary=_summarize_stage_outcome(stage_slug, completed.returncode, artifact_index),
        claude_stdout=completed.stdout.strip(),
        claude_stderr=completed.stderr.strip(),
        returncode=completed.returncode,
    )


def render_stage_report(
    *,
    stage_name: str,
    project_root: str | Path,
    command_log: list[str],
    artifact_index: dict[str, list[str]],
    outcome_summary: str,
    claude_stdout: str = "",
    claude_stderr: str = "",
) -> str:
    lines = [
        f"# {stage_name} Report",
        "",
        f"- Project root: `{Path(project_root).as_posix()}`",
        "",
        "## Outcome Summary",
        "",
        outcome_summary,
        "",
        "## Command Log",
        "",
    ]
    if command_log:
        lines.extend(f"- `{command}`" for command in command_log)
    else:
        lines.append("- No commands recorded.")
    lines.extend(["", "## Artifact Index", ""])
    if artifact_index:
        for bucket, entries in artifact_index.items():
            lines.append(f"### {bucket}")
            lines.append("")
            if entries:
                lines.extend(f"- `{entry}`" for entry in entries)
            else:
                lines.append("- None")
            lines.append("")
    else:
        lines.extend(["- No artifacts collected.", ""])
    lines.extend(
        [
            "## Claude Output",
            "",
            "### stdout",
            "",
            "```text",
            claude_stdout or "<empty>",
            "```",
            "",
            "### stderr",
            "",
            "```text",
            claude_stderr or "<empty>",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_stage_report(report_path: str | Path, report_text: str) -> Path:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_text, encoding="utf-8")
    return path


def run_stage(
    *,
    stage_slug: str,
    project_root: str | Path,
    repo_root: str | Path,
    genre: str,
    command_log: list[str] | None = None,
    report_date: str | None = None,
) -> Path:
    stage_config = build_stage_config(stage_slug, report_date=report_date or _current_report_date())
    result = invoke_claude_stage(
        stage_slug=stage_slug,
        project_root=project_root,
        repo_root=repo_root,
        genre=genre,
        command_log=command_log,
    )
    report = render_stage_report(
        stage_name=result.stage_name,
        project_root=result.project_root,
        command_log=result.command_log,
        artifact_index=result.artifact_index,
        outcome_summary=result.outcome_summary,
        claude_stdout=result.claude_stdout,
        claude_stderr=result.claude_stderr,
    )
    return write_stage_report(stage_config.report_path, report)


def _load_claude_stage_prompt_template() -> str:
    try:
        return _CLAUDE_STAGE_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"unable to load Claude stage prompt template at {_CLAUDE_STAGE_PROMPT_TEMPLATE_PATH}"
        ) from exc


def _collect_artifact_entries(directory: Path, filename: str | None = None) -> list[str]:
    if filename is not None:
        path = directory / filename
        return [path.resolve().as_posix()] if path.exists() else []
    if not directory.exists():
        return []
    entries: list[str] = []
    for path in sorted(directory.iterdir(), key=lambda candidate: candidate.name):
        entries.append(path.resolve().as_posix())
    return entries


def _stage_config(stage_slug: str) -> dict[str, object]:
    try:
        return _STAGE_CONFIGS[stage_slug]
    except KeyError as exc:
        raise ValueError(f"unknown stage slug: {stage_slug}") from exc


def _summarize_stage_outcome(
    stage_slug: str,
    returncode: int,
    artifact_index: dict[str, list[str]],
) -> str:
    if returncode == 0:
        run_count = len(artifact_index.get("runs", []))
        checkpoint_count = len(artifact_index.get("checkpoints", []))
        return (
            f"{stage_slug} invocation completed with exit code 0. "
            f"Collected {run_count} run artifact(s) and {checkpoint_count} checkpoint artifact(s)."
        )
    return f"{stage_slug} invocation failed with exit code {returncode}."


def _current_report_date() -> str:
    return date.today().isoformat()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a thin Claude-hosted Pizhi verification stage.")
    parser.add_argument("--stage", required=True, choices=sorted(_STAGE_CONFIGS))
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[2].as_posix())
    parser.add_argument("--genre", default="urban fantasy")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report_path = run_stage(
        stage_slug=args.stage,
        project_root=args.project_root,
        repo_root=args.repo_root,
        genre=args.genre,
    )
    print(report_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
