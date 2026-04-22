from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
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
    pizhi_outputs: list[tuple[str, str]]
    artifact_index: dict[str, list[str]]
    outcome_summary: str
    claude_stdout: str
    claude_stderr: str
    returncode: int
    report_path: Path | None = None


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
_ADVANCED_CHAPTER_STATUSES = {"outlined", "drafted", "reviewed", "compiled"}


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
    playbook_root: str | Path | None = None,
    target_chapters: int,
    genre: str,
) -> str:
    repo_root_path = Path(repo_root)
    playbook_root_path = Path(playbook_root) if playbook_root is not None else repo_root_path / "agents" / "pizhi"
    template = Template(_load_claude_stage_prompt_template())
    return template.substitute(
        stage_slug=stage_slug,
        project_root=Path(project_root).as_posix(),
        repo_root=repo_root_path.as_posix(),
        playbook_root=playbook_root_path.as_posix(),
        target_chapters=target_chapters,
        genre=genre,
        stop_rule=_render_stage_stop_rule(target_chapters),
        batch_rules=_render_stage_batch_rules(target_chapters),
        workflow_instructions=_render_stage_workflow(target_chapters, genre=genre),
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
    repo_root_path = Path(repo_root).resolve()
    playbook_root = repo_root_path / "agents" / "pizhi"
    stage_config = build_stage_config(stage_slug, report_date=_current_report_date())
    claude_command = _resolve_cli_command("claude")
    prompt = _build_claude_execution_prompt(
        render_claude_stage_prompt(
        stage_slug=stage_slug,
        project_root=root,
        repo_root=repo_root_path,
        playbook_root=playbook_root,
        target_chapters=stage_config.target_chapters,
        genre=genre,
        )
    )
    commands = [] if command_log is None else list(command_log)
    commands.append("claude --permission-mode bypassPermissions --add-dir <repo_root>/agents/pizhi -p <rendered prompt>")
    completed = subprocess.run(
        [
            claude_command,
            "--permission-mode",
            "bypassPermissions",
            "--add-dir",
            str(playbook_root),
            "-p",
            prompt,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=root,
    )
    artifact_index = collect_stage_artifacts(root)
    pizhi_outputs = collect_host_pizhi_outputs(root, artifact_index=artifact_index)
    effective_returncode, outcome_summary = evaluate_stage_outcome(
        stage_slug=stage_slug,
        returncode=completed.returncode,
        artifact_index=artifact_index,
        project_root=root,
    )
    return StageExecutionResult(
        stage_name=stage_config.slug.replace("stage", "Stage "),
        project_root=root,
        command_log=commands,
        pizhi_outputs=pizhi_outputs,
        artifact_index=artifact_index,
        outcome_summary=outcome_summary,
        claude_stdout=(completed.stdout or "").strip(),
        claude_stderr=(completed.stderr or "").strip(),
        returncode=effective_returncode,
    )


def collect_host_pizhi_outputs(
    project_root: str | Path,
    *,
    artifact_index: dict[str, list[str]] | None = None,
) -> list[tuple[str, str]]:
    artifacts = collect_stage_artifacts(project_root) if artifact_index is None else artifact_index
    outputs: list[tuple[str, str]] = []
    review_reports = artifacts.get("reports", [])
    if review_reports:
        outputs.append(("pizhi review --full", _read_output_preview(Path(review_reports[0]))))
    manuscript_paths = artifacts.get("manuscript", [])
    if manuscript_paths:
        outputs.append(("pizhi compile", _read_output_preview(_select_manuscript_preview_path(manuscript_paths))))
    return outputs


def render_stage_report(
    *,
    stage_name: str,
    project_root: str | Path,
    command_log: list[str],
    pizhi_outputs: list[tuple[str, str]] | None = None,
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
    lines.extend(["## Host-Observed Pizhi Outputs", ""])
    if pizhi_outputs:
        for command, output_text in pizhi_outputs:
            lines.extend(
                [
                    f"### {command}",
                    "",
                    "```text",
                    output_text or "<empty>",
                    "```",
                    "",
                ]
            )
    else:
        lines.extend(["- No host-driven Pizhi outputs captured.", ""])
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
) -> StageExecutionResult:
    stage_config = build_stage_config(
        stage_slug,
        report_date=report_date or _current_report_date(),
        docs_dir=Path(repo_root) / "docs" / "verification",
    )
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
        pizhi_outputs=result.pizhi_outputs,
        artifact_index=result.artifact_index,
        outcome_summary=result.outcome_summary,
        claude_stdout=result.claude_stdout,
        claude_stderr=result.claude_stderr,
    )
    report_path = write_stage_report(stage_config.report_path, report)
    return StageExecutionResult(
        stage_name=result.stage_name,
        project_root=result.project_root,
        command_log=result.command_log,
        pizhi_outputs=result.pizhi_outputs,
        artifact_index=result.artifact_index,
        outcome_summary=result.outcome_summary,
        claude_stdout=result.claude_stdout,
        claude_stderr=result.claude_stderr,
        returncode=result.returncode,
        report_path=report_path,
    )


def _load_claude_stage_prompt_template() -> str:
    try:
        return _CLAUDE_STAGE_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"unable to load Claude stage prompt template at {_CLAUDE_STAGE_PROMPT_TEMPLATE_PATH}"
        ) from exc


def _render_stage_batch_rules(target_chapters: int) -> str:
    if target_chapters <= 3:
        return ""
    return (
        "- Continue sessions may emit checkpoints in smaller chapter batches instead of the full target range.\n"
        f"- Do not treat the first `1-3` batch as stage completion for this stage.\n"
        f"- If the highest applied written chapter is still below `{target_chapters}`, run "
        "`pizhi continue resume --session-id <session_id>` again to generate the next batch.\n"
    )


def _render_stage_stop_rule(target_chapters: int) -> str:
    if target_chapters <= 3:
        return (
            f"- After you apply the write checkpoint for chapters `1-{target_chapters}`, do not run "
            "`pizhi continue resume` again.\n"
        )
    return (
        f"- After chapters `1-{target_chapters}` all have applied write checkpoints, do not run "
        "`pizhi continue resume` again.\n"
    )


def _render_stage_workflow(target_chapters: int, *, genre: str) -> str:
    if target_chapters <= 3:
        return (
            "1. If `.pizhi/config.yaml` is missing, run `pizhi init --project-name "
            f'"Urban Fantasy Validation" --genre "{genre}" --total-chapters 60 --per-volume 15 '
            '--pov "Third Person Limited"` and then `pizhi agent configure --agent-backend opencode --agent-command opencode`.\n'
            "2. Run `pizhi status`.\n"
            f"3. Run `pizhi continue run --count {target_chapters} --execute`.\n"
            "4. Capture the returned `session_id`.\n"
            f"5. Run `pizhi checkpoints --session-id <session_id>` and apply the outline checkpoint for chapters `1-{target_chapters}` with `pizhi checkpoint apply --id <checkpoint_id>`.\n"
            "6. Run `pizhi continue resume --session-id <session_id>`.\n"
            f"7. Run `pizhi checkpoints --session-id <session_id>` again and apply the generated write checkpoint for chapters `1-{target_chapters}`.\n"
            "8. If the session is `ready_to_resume` or `completed`, run `pizhi review --full`.\n"
            f"9. Run `pizhi compile --chapters 1-{target_chapters}`.\n"
            "10. Run `pizhi status` again and stop.\n"
        )

    return (
        "1. If `.pizhi/config.yaml` is missing, run `pizhi init --project-name "
        f'"Urban Fantasy Validation" --genre "{genre}" --total-chapters 60 --per-volume 15 '
        '--pov "Third Person Limited"` and then `pizhi agent configure --agent-backend opencode --agent-command opencode`.\n'
        "2. Run `pizhi status`.\n"
        f"3. Run `pizhi continue run --count {target_chapters} --execute`.\n"
        "4. Capture the returned `session_id`.\n"
        f"5. Loop until chapters `1-{target_chapters}` all have applied write checkpoints.\n"
        "6. In each loop iteration, run `pizhi checkpoints --session-id <session_id>` and inspect the next generated checkpoint for the next unfinished chapter range.\n"
        "7. If the next generated checkpoint is an outline checkpoint, apply it with `pizhi checkpoint apply --id <checkpoint_id>` and then run `pizhi continue resume --session-id <session_id>` to generate the paired write checkpoint for the same range.\n"
        "8. If the next generated checkpoint is a write checkpoint, apply it with `pizhi checkpoint apply --id <checkpoint_id>`.\n"
        f"9. After applying a write checkpoint, if the highest applied written chapter is still below `{target_chapters}`, run `pizhi continue resume --session-id <session_id>` again to generate the next batch.\n"
        f"10. Do not apply or generate checkpoints beyond chapters `1-{target_chapters}`. Stop the continue loop as soon as chapters `1-{target_chapters}` all have applied write checkpoints.\n"
        "11. Run `pizhi review --full`.\n"
        f"12. Run `pizhi compile --chapters 1-{target_chapters}`.\n"
        "13. Run `pizhi status` again and stop.\n"
    )


def _build_claude_execution_prompt(prompt: str) -> str:
    normalized_prompt = prompt.lstrip()
    if normalized_prompt.startswith("# "):
        _heading, _separator, remainder = normalized_prompt.partition("\n")
        normalized_prompt = remainder.lstrip()
    return normalized_prompt


def _resolve_cli_command(command_name: str) -> str:
    resolved = shutil.which(command_name)
    if resolved is None:
        raise RuntimeError(f"required command not found on PATH: {command_name}")
    return resolved


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


def _read_output_preview(path: Path, max_chars: int = 4000) -> str:
    try:
        content = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "<missing>"
    if len(content) <= max_chars:
        return content
    return f"{content[:max_chars].rstrip()}\n...[truncated]"


def _select_manuscript_preview_path(manuscript_paths: list[str]) -> Path:
    candidates = [Path(path) for path in manuscript_paths]
    return max(candidates, key=_manuscript_preview_sort_key)


def _manuscript_preview_sort_key(path: Path) -> tuple[int, int, str]:
    name = path.stem.lower()
    numbers = [int(match) for match in re.findall(r"\d+", name)]
    if numbers:
        return (1, numbers[-1], path.name.lower())
    return (0, 0, path.name.lower())


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


def evaluate_stage_outcome(
    *,
    stage_slug: str,
    returncode: int,
    artifact_index: dict[str, list[str]],
    project_root: str | Path,
) -> tuple[int, str]:
    issues: list[str] = []
    target_chapters = int(_stage_config(stage_slug)["target_chapters"])

    if returncode != 0:
        issues.append(f"{stage_slug} invocation failed with exit code {returncode}")

    if not artifact_index.get("runs"):
        issues.append("no run artifacts were produced")
    if not artifact_index.get("sessions"):
        issues.append("no continue session artifacts were produced")
    if not artifact_index.get("checkpoints"):
        issues.append("no checkpoint artifacts were produced")
    if not artifact_index.get("reports"):
        issues.append("review report was not generated")
    if not artifact_index.get("manuscript"):
        issues.append("compiled manuscript output was not generated")

    records, chapter_index_error = _load_chapter_index_records(project_root)
    if chapter_index_error is not None:
        issues.append(chapter_index_error)
    elif records is None:
        issues.append("chapter index was not generated")
    else:
        issues.extend(_validate_target_chapters(records, target_chapters))
        issues.extend(_validate_no_overshoot(records, target_chapters))

    if issues:
        effective_returncode = returncode if returncode != 0 else 1
        return effective_returncode, f"{stage_slug} validation failed: {'; '.join(issues)}."

    return returncode, _summarize_stage_outcome(stage_slug, returncode, artifact_index)


def _load_chapter_index_records(project_root: str | Path) -> tuple[list[dict[str, object]] | None, str | None]:
    index_path = Path(project_root) / ".pizhi" / "chapters" / "index.jsonl"
    if not index_path.exists():
        return None, None
    records: list[dict[str, object]] = []
    try:
        for raw_line in index_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            record = json.loads(line)
            if not isinstance(record, dict) or "n" not in record:
                return None, "chapter index schema is invalid"
            try:
                record["n"] = int(record["n"])
            except (TypeError, ValueError):
                return None, "chapter index schema is invalid"
            records.append(record)
    except json.JSONDecodeError:
        return None, "chapter index could not be parsed"
    return records, None


def _validate_target_chapters(records: list[dict[str, object]], target_chapters: int) -> list[str]:
    record_map = {int(record["n"]): record for record in records if "n" in record}
    issues: list[str] = []
    missing = [number for number in range(1, target_chapters + 1) if number not in record_map]
    if missing:
        rendered = ", ".join(f"ch{number:03d}" for number in missing)
        issues.append(f"target chapters are missing from the chapter index: {rendered}")
        return issues

    not_compiled = [
        number
        for number in range(1, target_chapters + 1)
        if str(record_map[number].get("status")) != "compiled"
    ]
    if not_compiled:
        rendered = ", ".join(
            f"ch{number:03d} ({record_map[number].get('status', 'missing')})" for number in not_compiled
        )
        issues.append(f"target chapters did not reach compiled status: {rendered}")
    return issues


def _validate_no_overshoot(records: list[dict[str, object]], target_chapters: int) -> list[str]:
    advanced = [
        record
        for record in records
        if int(record.get("n", 0)) > target_chapters
        and str(record.get("status")) in _ADVANCED_CHAPTER_STATUSES
    ]
    if not advanced:
        return []
    rendered = ", ".join(
        f"ch{int(record['n']):03d} ({record.get('status', 'unknown')})" for record in advanced
    )
    return [f"chapters beyond 1-{target_chapters} advanced unexpectedly: {rendered}"]


def _current_report_date() -> str:
    return date.today().isoformat()


def _current_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_validation_base_dir(repo_root: str | Path) -> Path:
    root = Path(repo_root).resolve()
    if root.parent.name == ".worktrees":
        return root.parents[2] / "tmp"
    return root.parent / "tmp"


def _default_project_root(repo_root: str | Path) -> Path:
    return build_validation_root_path(
        _current_timestamp(),
        base_dir=_default_validation_base_dir(repo_root),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a thin Claude-hosted Pizhi verification stage.")
    parser.add_argument("--stage", required=True, choices=sorted(_STAGE_CONFIGS))
    parser.add_argument("--project-root")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[2].as_posix())
    parser.add_argument("--genre", default="urban fantasy")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    project_root = Path(args.project_root) if args.project_root else _default_project_root(args.repo_root)
    project_root.mkdir(parents=True, exist_ok=True)
    result = run_stage(
        stage_slug=args.stage,
        project_root=project_root,
        repo_root=args.repo_root,
        genre=args.genre,
    )
    if result.report_path is not None:
        print(result.report_path.as_posix())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
