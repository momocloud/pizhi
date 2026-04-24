from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
from string import Template
import subprocess
import tempfile


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


@dataclass(frozen=True, slots=True)
class ClaudeStageStep:
    prompt: str
    prompt_kind: str
    batch_range: tuple[int, int] | None
    allowed_max_chapter: int
    allowed_command_fragments: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProcessEntry:
    process_id: int
    parent_process_id: int
    commandline: str


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
_DRAFTED_CHAPTER_STATUSES = {"drafted", "reviewed", "compiled"}
_WATCHDOG_INTERVAL_SECONDS = 15 * 60
_WATCHDOG_FAILURE_RETURNCODE = 124


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
    playbook_root = (root.parent / "overlay_playbook").resolve()
    stage_config = build_stage_config(stage_slug, report_date=_current_report_date())
    claude_command = _resolve_cli_command("claude")
    commands = [] if command_log is None else list(command_log)
    steps = _build_claude_stage_steps(
        stage_slug=stage_slug,
        project_root=root,
        repo_root=repo_root_path,
        playbook_root=playbook_root,
        target_chapters=stage_config.target_chapters,
        genre=genre,
    )
    completed_runs: list[subprocess.CompletedProcess[str]] = []
    for step in steps:
        preflight_issues = build_single_flight_issues(repo_root=repo_root_path, project_root=root)
        if preflight_issues:
            completed_runs.append(
                subprocess.CompletedProcess(
                    args=["preflight"],
                    returncode=1,
                    stdout="",
                    stderr=f"PREFLIGHT: {'; '.join(preflight_issues)}",
                )
            )
            break
        _build_stage_overlay_playbook(
            stage_slug=stage_slug,
            project_root=root,
            repo_root=repo_root_path,
            target_chapters=stage_config.target_chapters,
            genre=genre,
            step=step,
        )
        commands.append(f"claude --permission-mode bypassPermissions --add-dir {playbook_root} -p <rendered prompt>")
        completed = _run_claude_stage_step(
            claude_command=claude_command,
            playbook_root=playbook_root,
            project_root=root,
            stage_slug=stage_slug,
            step=step,
        )
        completed_runs.append(completed)
        if completed.returncode == 0:
            postflight_issues = build_stage_step_state_issues(
                project_root=root,
                stage_slug=stage_slug,
                step=step,
            )
            if postflight_issues:
                completed_runs[-1] = subprocess.CompletedProcess(
                    args=completed.args,
                    returncode=1,
                    stdout=completed.stdout,
                    stderr="\n".join(
                        part
                        for part in [completed.stderr, f"POSTFLIGHT: {'; '.join(postflight_issues)}"]
                        if part
                    ),
                )
                break
        if completed.returncode != 0:
            break

    final_completed = completed_runs[-1]
    artifact_index = collect_stage_artifacts(root)
    pizhi_outputs = collect_host_pizhi_outputs(root, artifact_index=artifact_index)
    effective_returncode, outcome_summary = evaluate_stage_outcome(
        stage_slug=stage_slug,
        returncode=final_completed.returncode,
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
        claude_stdout="\n\n".join(
            output
            for output in ((completed.stdout or "").strip() for completed in completed_runs)
            if output
        ),
        claude_stderr="\n\n".join(
            output
            for output in ((completed.stderr or "").strip() for completed in completed_runs)
            if output
        ),
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
            "3. Run `pizhi brainstorm --execute`.\n"
            "4. Capture the returned `run_id`.\n"
            "5. Run `pizhi apply --run-id <run_id>`.\n"
            f"6. Run `pizhi continue run --count {target_chapters} --execute`.\n"
            "7. Capture the returned `session_id`.\n"
            f"8. Run `pizhi checkpoints --session-id <session_id>` and apply the outline checkpoint for chapters `1-{target_chapters}` with `pizhi checkpoint apply --id <checkpoint_id>`.\n"
            "9. Run `pizhi continue resume --session-id <session_id>`.\n"
            f"10. Run `pizhi checkpoints --session-id <session_id>` again and apply the generated write checkpoint for chapters `1-{target_chapters}`.\n"
            "11. If the session is `ready_to_resume` or `completed`, run `pizhi review --full`.\n"
            f"12. Run `pizhi compile --chapters 1-{target_chapters}`.\n"
            "13. Run `pizhi status` again and stop.\n"
        )

    lines = [
        "1. If `.pizhi/config.yaml` is missing, run `pizhi init --project-name "
        f'"Urban Fantasy Validation" --genre "{genre}" --total-chapters 60 --per-volume 15 '
        '--pov "Third Person Limited"` and then `pizhi agent configure --agent-backend opencode --agent-command opencode`.',
        "2. Run `pizhi status`.",
        "3. Run `pizhi brainstorm --execute`.",
        "4. Capture the returned `run_id`.",
        "5. Run `pizhi apply --run-id <run_id>`.",
        f"6. Run `pizhi continue run --count {target_chapters} --execute`.",
        "7. Capture the returned `session_id`.",
    ]
    step_number = 8
    batch_ranges = _stage_batch_ranges(target_chapters)
    for index, (start, end) in enumerate(batch_ranges):
        lines.append(
            f"{step_number}. Run `pizhi checkpoints --session-id <session_id>` and apply the outline checkpoint for chapters `{start}-{end}` with `pizhi checkpoint apply --id <checkpoint_id>`."
        )
        step_number += 1
        lines.append(
            f"{step_number}. Run `pizhi continue resume --session-id <session_id>` to generate the write checkpoint for chapters `{start}-{end}`."
        )
        step_number += 1
        lines.append(
            f"{step_number}. Run `pizhi checkpoints --session-id <session_id>` again and apply the write checkpoint for chapters `{start}-{end}`."
        )
        step_number += 1
        if index < len(batch_ranges) - 1:
            lines.append(
                f"{step_number}. Run `pizhi continue resume --session-id <session_id>` again to generate the next outline checkpoint batch."
            )
            step_number += 1
        else:
            lines.append(
                f"{step_number}. After you apply the write checkpoint for chapters `{start}-{end}`, stop the continue loop."
            )
            step_number += 1

    lines.extend(
        [
            f"{step_number}. Run `pizhi review --full`.",
            f"{step_number + 1}. Run `pizhi compile --chapters 1-{target_chapters}`.",
            f"{step_number + 2}. Run `pizhi status` again and stop.",
        ]
    )
    return "\n".join(lines) + "\n"


def _stage_batch_ranges(target_chapters: int, batch_size: int = 3) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 1
    while start <= target_chapters:
        end = min(target_chapters, start + batch_size - 1)
        ranges.append((start, end))
        start = end + 1
    return ranges


def _build_claude_stage_prompts(
    *,
    stage_slug: str,
    project_root: str | Path,
    repo_root: str | Path,
    playbook_root: str | Path,
    target_chapters: int,
    genre: str,
) -> list[str]:
    return [
        step.prompt
        for step in _build_claude_stage_steps(
            stage_slug=stage_slug,
            project_root=project_root,
            repo_root=repo_root,
            playbook_root=playbook_root,
            target_chapters=target_chapters,
            genre=genre,
        )
    ]


def _build_claude_stage_steps(
    *,
    stage_slug: str,
    project_root: str | Path,
    repo_root: str | Path,
    playbook_root: str | Path,
    target_chapters: int,
    genre: str,
) -> list[ClaudeStageStep]:
    if target_chapters <= 3:
        return [
            ClaudeStageStep(
                prompt=_build_claude_execution_prompt(
                    render_claude_stage_prompt(
                        stage_slug=stage_slug,
                        project_root=project_root,
                        repo_root=repo_root,
                        playbook_root=playbook_root,
                        target_chapters=target_chapters,
                        genre=genre,
                    )
                ),
                prompt_kind="single",
                batch_range=(1, target_chapters),
                allowed_max_chapter=target_chapters,
                allowed_command_fragments=_build_allowed_command_fragments(
                    prompt_kind="single",
                    target_chapters=target_chapters,
                ),
            )
        ]

    batch_ranges = _stage_batch_ranges(target_chapters)
    steps = [
        ClaudeStageStep(
            prompt=_build_claude_execution_prompt(
                _render_batched_claude_stage_prompt(
                    stage_slug=stage_slug,
                    project_root=project_root,
                    repo_root=repo_root,
                    playbook_root=playbook_root,
                    target_chapters=target_chapters,
                    genre=genre,
                    batch_range=batch_ranges[0],
                    prompt_kind="initial",
                )
            ),
            prompt_kind="initial",
            batch_range=batch_ranges[0],
            allowed_max_chapter=batch_ranges[0][1],
            allowed_command_fragments=_build_allowed_command_fragments(
                prompt_kind="initial",
                target_chapters=target_chapters,
            ),
        )
    ]
    for batch_range in batch_ranges[1:]:
        steps.append(
            ClaudeStageStep(
                prompt=_build_claude_execution_prompt(
                    _render_batched_claude_stage_prompt(
                        stage_slug=stage_slug,
                        project_root=project_root,
                        repo_root=repo_root,
                        playbook_root=playbook_root,
                        target_chapters=target_chapters,
                        genre=genre,
                        batch_range=batch_range,
                        prompt_kind="resume",
                    )
                ),
                prompt_kind="resume",
                batch_range=batch_range,
                allowed_max_chapter=batch_range[1],
                allowed_command_fragments=_build_allowed_command_fragments(
                    prompt_kind="resume",
                    target_chapters=target_chapters,
                ),
            )
        )
    steps.append(
        ClaudeStageStep(
            prompt=_build_claude_execution_prompt(
                _render_batched_claude_stage_prompt(
                    stage_slug=stage_slug,
                    project_root=project_root,
                    repo_root=repo_root,
                    playbook_root=playbook_root,
                    target_chapters=target_chapters,
                    genre=genre,
                    batch_range=batch_ranges[-1],
                    prompt_kind="finalization",
                )
            ),
            prompt_kind="finalization",
            batch_range=batch_ranges[-1],
            allowed_max_chapter=target_chapters,
            allowed_command_fragments=_build_allowed_command_fragments(
                prompt_kind="finalization",
                target_chapters=target_chapters,
            ),
        )
    )
    return steps


def _build_stage_overlay_playbook(
    *,
    stage_slug: str,
    project_root: str | Path,
    repo_root: str | Path,
    target_chapters: int,
    genre: str,
    step: ClaudeStageStep,
) -> Path:
    root = Path(project_root).resolve()
    repo_root_path = Path(repo_root).resolve()
    overlay_root = root.parent / "overlay_playbook"
    resources_root = overlay_root / "resources"
    resources_root.mkdir(parents=True, exist_ok=True)

    batch_range = step.batch_range or (1, target_chapters)
    start, end = batch_range
    agents_lines = [
        "# Pizhi E2E Stage Playbook",
        "",
        "Stage prompt is the only authority for this validation step.",
        "",
        "Read only these local resources before running commands:",
        "",
        "- `resources/stage.md`",
        "- `resources/allowed-commands.md`",
        "",
        "Do not read or apply the general `agents/pizhi/resources/workflow.md` or `agents/pizhi/resources/examples.md` files.",
        "Do not infer alternative counts, project names, total chapter counts, or chapter ranges from examples.",
        "Run only the commands listed for this exact step, in order, and stop when the step says to stop.",
        "",
    ]
    stage_lines = [
        "# Stage Context",
        "",
        f"Stage: `{stage_slug}`",
        f"Step kind: `{step.prompt_kind}`",
        f"Project root: `{root.as_posix()}`",
        f"Repository root: `{repo_root_path.as_posix()}`",
        f"Target chapters: `{target_chapters}`",
        f"Genre: `{genre}`",
        f"Batch range: `{start}-{end}`",
        f"Allowed max chapter during this step: `ch{step.allowed_max_chapter:03d}`",
        "",
        "Use the command sequence in `allowed-commands.md` as the only valid workflow for this step.",
        "If any command fails, report the failure and stop the step.",
        "",
    ]
    commands_lines = [
        "# Allowed Commands",
        "",
        "Run only commands matching this step. Do not substitute a different count or chapter range.",
        "",
        *_render_overlay_allowed_commands(
            prompt_kind=step.prompt_kind,
            target_chapters=target_chapters,
            batch_range=batch_range,
            genre=genre,
        ),
        "",
    ]

    (overlay_root / "AGENTS.md").write_text("\n".join(agents_lines), encoding="utf-8")
    (resources_root / "stage.md").write_text("\n".join(stage_lines), encoding="utf-8")
    (resources_root / "allowed-commands.md").write_text("\n".join(commands_lines), encoding="utf-8")
    return overlay_root


def _render_overlay_allowed_commands(
    *,
    prompt_kind: str,
    target_chapters: int,
    batch_range: tuple[int, int],
    genre: str,
) -> list[str]:
    start, end = batch_range
    if prompt_kind in {"single", "initial"}:
        commands = [
            f'1. `pizhi init --project-name "Urban Fantasy Validation" --genre "{genre}" --total-chapters 60 --per-volume 15 --pov "Third Person Limited"`',
            "2. `pizhi agent configure --agent-backend opencode --agent-command opencode`",
            "3. `pizhi status`",
            "4. `pizhi brainstorm --execute`",
            "5. `pizhi apply --run-id <run_id>`",
            f"6. `pizhi continue run --count {target_chapters} --execute`",
            "7. `pizhi checkpoints --session-id <session_id>`",
            f"8. Apply the outline checkpoint for chapters `{start}-{end}` with `pizhi checkpoint apply --id <checkpoint_id>`.",
            "9. `pizhi continue resume --session-id <session_id>`",
            f"10. Apply the write checkpoint for chapters `{start}-{end}` with `pizhi checkpoint apply --id <checkpoint_id>`.",
        ]
        if prompt_kind == "single":
            commands.extend(
                [
                    "11. `pizhi review --full`",
                    f"12. `pizhi compile --chapters 1-{target_chapters}`",
                ]
            )
        return commands
    if prompt_kind == "resume":
        return [
            "1. `pizhi status`",
            "2. `pizhi continue resume --session-id <session_id>`",
            "3. `pizhi checkpoints --session-id <session_id>`",
            f"4. apply the outline checkpoint for chapters `{start}-{end}` with `pizhi checkpoint apply --id <checkpoint_id>`.",
            "5. Do not stop after applying the outline checkpoint.",
            f"6. Run `pizhi continue resume --session-id <session_id>` again to generate the write checkpoint for chapters `{start}-{end}`.",
            "7. `pizhi checkpoints --session-id <session_id>`",
            f"8. apply the write checkpoint for chapters `{start}-{end}` with `pizhi checkpoint apply --id <checkpoint_id>`.",
            "9. Stop this step after applying the write checkpoint.",
        ]
    if prompt_kind == "finalization":
        return [
            "1. `pizhi review --full`",
            f"2. `pizhi compile --chapters 1-{target_chapters}`",
            "3. `pizhi status`",
        ]
    raise ValueError(f"unknown prompt kind: {prompt_kind}")


def _build_allowed_command_fragments(
    *,
    prompt_kind: str,
    target_chapters: int,
) -> tuple[str, ...]:
    fragments: list[str] = [r"status"]
    if prompt_kind in {"single", "initial"}:
        fragments.extend(
            [
                r"init\s+--project-name\s+(?:\"[^\"]+\"|\S+)\s+--genre\s+(?:\"[^\"]+\"|\S+)\s+--total-chapters\s+60\s+--per-volume\s+15\s+--pov\s+(?:\"[^\"]+\"|\S+)",
                r"agent\s+configure\s+--agent-backend\s+opencode\s+--agent-command\s+opencode",
                r"brainstorm\s+--execute",
                r"apply\s+--run-id\s+\S+",
                fr"continue\s+run\s+--count\s+{target_chapters}\s+--execute",
                r"checkpoints\s+--session-id\s+\S+",
                r"checkpoint\s+apply\s+--id\s+\S+",
                r"continue\s+resume\s+--session-id\s+\S+",
            ]
        )
    elif prompt_kind == "resume":
        fragments.extend(
            [
                r"continue\s+resume\s+--session-id\s+\S+",
                r"checkpoints\s+--session-id\s+\S+",
                r"checkpoint\s+apply\s+--id\s+\S+",
            ]
        )
    elif prompt_kind == "finalization":
        fragments.extend(
            [
                r"review\s+--full",
                fr"compile\s+--chapters\s+1-{target_chapters}",
            ]
        )
    else:
        raise ValueError(f"unknown prompt kind: {prompt_kind}")

    if prompt_kind == "single":
        fragments.extend(
            [
                r"review\s+--full",
                fr"compile\s+--chapters\s+1-{target_chapters}",
            ]
        )

    unique_fragments: list[str] = []
    for fragment in fragments:
        if fragment not in unique_fragments:
            unique_fragments.append(fragment)
    return tuple(unique_fragments)


def _run_claude_stage_step(
    *,
    claude_command: str,
    playbook_root: Path,
    project_root: Path,
    stage_slug: str,
    step: ClaudeStageStep,
) -> subprocess.CompletedProcess[str]:
    command = [
        claude_command,
        "--permission-mode",
        "bypassPermissions",
        "--add-dir",
            str(playbook_root),
            "-p",
            step.prompt,
        ]
    _write_project_stage_anchor(project_root=project_root, step=step)
    popen_cls = getattr(subprocess, "Popen", None)
    if popen_cls is None:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            cwd=project_root,
        )

    with tempfile.TemporaryDirectory(
        prefix="pizhi-claude-stage-step-",
        ignore_cleanup_errors=True,
    ) as capture_dir:
        stdout_path = Path(capture_dir) / "stdout.txt"
        stderr_path = Path(capture_dir) / "stderr.txt"
        with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_handle, stderr_path.open(
            "w",
            encoding="utf-8",
            errors="replace",
        ) as stderr_handle:
            process = popen_cls(
                command,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=project_root,
            )
            while True:
                try:
                    returncode = process.wait(timeout=_WATCHDOG_INTERVAL_SECONDS)
                    stdout_handle.flush()
                    stderr_handle.flush()
                    return subprocess.CompletedProcess(
                        args=command,
                        returncode=0 if returncode is None else returncode,
                        stdout=stdout_path.read_text(encoding="utf-8", errors="replace"),
                        stderr=stderr_path.read_text(encoding="utf-8", errors="replace"),
                    )
                except subprocess.TimeoutExpired:
                    issues = build_stage_watchdog_issues(
                        project_root=project_root,
                        stage_slug=stage_slug,
                        step=step,
                        root_pid=getattr(process, "pid", None),
                    )
                    if not issues:
                        continue
                    try:
                        process.kill()
                    except OSError:
                        pass
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                    stdout_handle.flush()
                    stderr_handle.flush()
                    watchdog_message = f"WATCHDOG: {'; '.join(issues)}"
                    combined_stderr = "\n".join(
                        part
                        for part in [
                            stderr_path.read_text(encoding="utf-8", errors="replace"),
                            watchdog_message,
                        ]
                        if part
                    )
                    return subprocess.CompletedProcess(
                        args=command,
                        returncode=_WATCHDOG_FAILURE_RETURNCODE,
                        stdout=stdout_path.read_text(encoding="utf-8", errors="replace"),
                        stderr=combined_stderr,
                    )


def _write_project_stage_anchor(*, project_root: Path, step: ClaudeStageStep) -> None:
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "AGENTS.md").write_text(
        "\n".join(
            [
                "# Pizhi Validation Task",
                "",
                "This directory is a temporary Pizhi validation project.",
                "The project may be empty before `pizhi init`; this is expected.",
                "Do not ask for additional context. Follow `STAGE_TASK.md` exactly.",
                "Only mutate Pizhi project state by running the `pizhi` CLI commands specified in `STAGE_TASK.md`.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    (project_root / "STAGE_TASK.md").write_text(step.prompt, encoding="utf-8", newline="\n")


def _render_batched_claude_stage_prompt(
    *,
    stage_slug: str,
    project_root: str | Path,
    repo_root: str | Path,
    playbook_root: str | Path,
    target_chapters: int,
    genre: str,
    batch_range: tuple[int, int],
    prompt_kind: str,
) -> str:
    project_root_path = Path(project_root)
    repo_root_path = Path(repo_root)
    playbook_root_path = Path(playbook_root)
    start, end = batch_range
    lines = [
        "# Claude Stage Prompt",
        "",
        "Execute this validation stage now in the current working directory.",
        f"Stage: `{stage_slug}`",
        f"Project root: `{project_root_path.as_posix()}`",
        f"Repository root: `{repo_root_path.as_posix()}`",
        f"Playbook root: `{playbook_root_path.as_posix()}`",
        f"Target chapters: `{target_chapters}`",
        f"Genre: `{genre}`",
        "",
        "Rules:",
        "- The repo/playbook are read-only. Only modify the temp project.",
        "- The current working directory may be empty before `pizhi init`; this is expected.",
        "- Do not ask for additional context because this prompt contains the validation context.",
        "- Do not edit project files directly; use `pizhi` commands only.",
        "- Execute only the exact `pizhi` commands listed below, in order.",
        "- Do not run any other `pizhi` commands.",
        "",
    ]
    if prompt_kind == "initial":
        lines.append("- Forbidden examples: `pizhi write --chapter ...`, `pizhi outline expand`, and any direct command not listed for this step.")
        lines.append("")
    else:
        lines.append("- Forbidden examples: `pizhi write --chapter ...`, `pizhi brainstorm`, `pizhi outline expand`, and any direct command not listed for this step.")
        lines.append("")
    if prompt_kind == "initial":
        lines.extend(
            [
                f"- During this step, do not advance chapters beyond `{start}-{end}`.",
                "",
                "Workflow:",
                f"1. If `.pizhi/config.yaml` is missing, run `pizhi init --project-name \"Urban Fantasy Validation\" --genre \"{genre}\" --total-chapters 60 --per-volume 15 --pov \"Third Person Limited\"` and then `pizhi agent configure --agent-backend opencode --agent-command opencode`.",
                "2. Run `pizhi status`.",
                "3. Run `pizhi brainstorm --execute`.",
                "4. Capture the returned `run_id`.",
                "5. Run `pizhi apply --run-id <run_id>`.",
                f"6. Run `pizhi continue run --count {target_chapters} --execute`.",
                "7. Capture the returned `session_id`.",
                f"8. Run `pizhi checkpoints --session-id <session_id>` and apply the outline checkpoint for chapters `{start}-{end}` with `pizhi checkpoint apply --id <checkpoint_id>`.",
                f"9. Run `pizhi continue resume --session-id <session_id>`.",
                f"10. Run `pizhi checkpoints --session-id <session_id>` again and apply the write checkpoint for chapters `{start}-{end}`.",
            ]
        )
    elif prompt_kind == "resume":
        lines.extend(
            [
                f"- During this step, do not advance chapters beyond `{start}-{end}`.",
                "- Resolve `<session_id>` from `pizhi status` or the latest `.pizhi/cache/continue_sessions/*/manifest.json`.",
                "- Never run a command with the literal `<session_id>` placeholder.",
                "- Do not stop after applying the outline checkpoint; the step is incomplete until the write checkpoint is applied.",
                "- Do not run `pizhi review`, do not analyze quality, and do not ask whether to apply fixes in this step.",
                "",
                "Workflow:",
                "1. Run `pizhi status`.",
                "2. Run `pizhi continue resume --session-id <session_id>`.",
                f"3. Run `pizhi checkpoints --session-id <session_id>` and apply the outline checkpoint for chapters `{start}-{end}` with `pizhi checkpoint apply --id <checkpoint_id>`.",
                "4. Run `pizhi continue resume --session-id <session_id>` again.",
                f"5. Run `pizhi checkpoints --session-id <session_id>` again and apply the write checkpoint for chapters `{start}-{end}`.",
            ]
        )
    elif prompt_kind == "finalization":
        lines.extend(
            [
                "- Finalization is read-only with respect to continue sessions. Do not generate new checkpoints in this step.",
                "",
                "Workflow:",
                "1. Run `pizhi status`.",
                "2. Run `pizhi review --full`.",
                f"3. Run `pizhi compile --chapters 1-{target_chapters}`.",
                "4. Run `pizhi status` again and stop.",
            ]
        )
    else:
        raise ValueError(f"unknown prompt kind: {prompt_kind}")
    return "\n".join(lines) + "\n"


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


def build_stage_watchdog_issues(
    *,
    project_root: str | Path,
    stage_slug: str,
    step: ClaudeStageStep,
    root_pid: int | None = None,
) -> list[str]:
    root = Path(project_root)
    issues: list[str] = []
    issues.extend(
        _load_blocked_session_issues(
            root,
            target_end_chapter=int(_stage_config(stage_slug)["target_chapters"]),
        )
    )
    records, chapter_index_error = _load_chapter_index_records(root)
    if chapter_index_error is not None:
        issues.append(f"chapter index watchdog check failed: {chapter_index_error}")
    elif records is not None:
        issues.extend(_validate_watchdog_no_overshoot(records, step.allowed_max_chapter))

    process_entries = (
        _list_running_process_entries(root_pid=root_pid)
        if root_pid is not None
        else _list_running_process_entries()
    )
    if root_pid is not None and _watchdog_process_tree_is_stalled(process_entries, root_pid=root_pid):
        issues.append("step appears stalled: no active child processes remain")

    process_commandlines = (
        _list_running_process_commandlines(root_pid=root_pid)
        if root_pid is not None
        else _list_running_process_commandlines()
    )
    for commandline in process_commandlines:
        for pizhi_command in _extract_running_pizhi_commands(commandline):
            if _is_allowed_running_pizhi_command(pizhi_command, step.allowed_command_fragments):
                continue
            issues.append(f"disallowed running command detected: pizhi {pizhi_command}")
    return issues


def build_stage_step_state_issues(
    *,
    project_root: str | Path,
    stage_slug: str,
    step: ClaudeStageStep,
) -> list[str]:
    root = Path(project_root)
    issues: list[str] = []
    issues.extend(
        _load_blocked_session_issues(
            root,
            target_end_chapter=int(_stage_config(stage_slug)["target_chapters"]),
        )
    )
    records, chapter_index_error = _load_chapter_index_records(root)
    if chapter_index_error is not None:
        issues.append(f"chapter index postflight check failed: {chapter_index_error}")
    elif records is None and step.prompt_kind in {"initial", "resume"} and step.batch_range is not None:
        issues.append("chapter index was not generated for this step")
    elif records is not None:
        issues.extend(_validate_watchdog_no_overshoot(records, step.allowed_max_chapter))
        issues.extend(_validate_step_batch_write_progress(records, step))
    return issues


def build_single_flight_issues(
    *,
    repo_root: str | Path,
    project_root: str | Path,
) -> list[str]:
    repo_root_path = Path(repo_root).resolve()
    project_root_path = Path(project_root).resolve()
    current_pid = os.getpid()
    issues: list[str] = []
    repo_marker = _normalize_process_match_text(repo_root_path.as_posix())
    project_marker = _normalize_process_match_text(project_root_path.as_posix())
    playbook_marker = _normalize_process_match_text((repo_root_path / "agents" / "pizhi").as_posix())
    for entry in _list_running_process_entries():
        if entry.process_id == current_pid:
            continue
        normalized = _normalize_process_match_text(entry.commandline)
        if not normalized:
            continue
        if _is_process_listing_commandline(normalized):
            continue
        if "e2e_claude_opencode.py --stage" in normalized:
            issues.append(f"existing validation harness process detected: pid {entry.process_id}")
            continue
        if playbook_marker in normalized and "claude" in normalized:
            issues.append(f"existing Claude playbook process detected: pid {entry.process_id}")
            continue
        if project_marker in normalized and "pizhi" in normalized:
            issues.append(f"existing project-scoped pizhi process detected: pid {entry.process_id}")
            continue
        if repo_marker in normalized and "pizhi-e2e-claude-opencode-" in normalized and ("pizhi" in normalized or "claude" in normalized or "opencode" in normalized):
            issues.append(f"existing validation temp process detected: pid {entry.process_id}")
            continue
        if "pizhi-opencode-" in normalized and "opencode" in normalized:
            issues.append(f"existing validation opencode process detected: pid {entry.process_id}")
            continue
    return issues


def _normalize_process_match_text(value: str) -> str:
    return value.replace("\\", "/").lower()


def _is_process_listing_commandline(commandline: str) -> bool:
    return "get-ciminstance win32_process" in commandline or "get-wmiobject win32_process" in commandline


def _load_blocked_session_issues(project_root: Path, *, target_end_chapter: int) -> list[str]:
    sessions_root = project_root / ".pizhi" / "cache" / "continue_sessions"
    if not sessions_root.exists():
        return []
    matching_sessions: list[tuple[datetime, dict[str, object], Path]] = []
    for manifest_path in sorted(sessions_root.glob("*/manifest.json")):
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        try:
            manifest_target = int(payload.get("target_end_chapter"))
        except (TypeError, ValueError):
            continue
        if manifest_target != target_end_chapter:
            continue
        matching_sessions.append((_session_manifest_timestamp(payload, manifest_path), payload, manifest_path))
    if not matching_sessions:
        return []
    _updated_at, payload, manifest_path = max(matching_sessions, key=lambda item: item[0])
    if str(payload.get("status")) != "blocked":
        return []
    session_id = str(payload.get("session_id") or manifest_path.parent.name)
    return [f"session {session_id} is blocked"]


def _session_manifest_timestamp(payload: dict[str, object], manifest_path: Path) -> datetime:
    updated_at = payload.get("updated_at")
    if isinstance(updated_at, str):
        normalized = updated_at.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.fromtimestamp(manifest_path.stat().st_mtime)


def _validate_watchdog_no_overshoot(
    records: list[dict[str, object]],
    allowed_max_chapter: int,
) -> list[str]:
    advanced = [
        record
        for record in records
        if int(record.get("n", 0)) > allowed_max_chapter
        and str(record.get("status")) in _ADVANCED_CHAPTER_STATUSES
    ]
    if not advanced:
        return []
    rendered = ", ".join(
        f"ch{int(record['n']):03d} ({record.get('status', 'unknown')})" for record in advanced
    )
    return [f"chapters beyond ch{allowed_max_chapter:03d} advanced unexpectedly: {rendered}"]


def _validate_step_batch_write_progress(records: list[dict[str, object]], step: ClaudeStageStep) -> list[str]:
    if step.prompt_kind not in {"initial", "resume"} or step.batch_range is None:
        return []
    start, end = step.batch_range
    record_map = {int(record["n"]): record for record in records if "n" in record}
    missing_or_unwritten = [
        number
        for number in range(start, end + 1)
        if str(record_map.get(number, {}).get("status")) not in _DRAFTED_CHAPTER_STATUSES
    ]
    if not missing_or_unwritten:
        return []
    rendered = ", ".join(f"ch{number:03d}" for number in missing_or_unwritten)
    return [f"expected drafted chapters for this step are missing: {rendered}"]


def _watchdog_process_tree_is_stalled(entries: list[ProcessEntry], *, root_pid: int) -> bool:
    root_present = False
    for entry in entries:
        if entry.process_id == root_pid:
            root_present = True
            continue
        normalized = _normalize_process_match_text(entry.commandline)
        if not normalized:
            continue
        if _is_ignorable_watchdog_descendant(normalized):
            continue
        return False
    return root_present


def _is_ignorable_watchdog_descendant(commandline: str) -> bool:
    return "conhost.exe" in commandline or commandline.startswith("/??/c:/windows/system32/conhost.exe")


def _list_running_process_commandlines(root_pid: int | None = None) -> list[str]:
    return [entry.commandline for entry in _list_running_process_entries(root_pid=root_pid)]


def _list_running_process_entries(root_pid: int | None = None) -> list[ProcessEntry]:
    if os.name == "nt":
        shell = shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")
        if shell is None:
            return []
        completed = subprocess.run(
            [
                shell,
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine } | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    else:
        completed = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,command="],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    if completed.returncode != 0:
        return []
    stdout = (completed.stdout or "").strip()
    if not stdout:
        return []
    if os.name == "nt":
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return []
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            return []
        process_entries = [
            ProcessEntry(
                process_id=int(entry.get("ProcessId")),
                parent_process_id=int(entry.get("ParentProcessId")),
                commandline=str(entry.get("CommandLine")).strip(),
            )
            for entry in payload
            if isinstance(entry, dict)
            and str(entry.get("CommandLine", "")).strip()
            and isinstance(entry.get("ProcessId"), (int, float, str))
            and isinstance(entry.get("ParentProcessId"), (int, float, str))
        ]
        return _filter_process_entries(process_entries, root_pid=root_pid)
    process_entries: list[ProcessEntry] = []
    for line in stdout.splitlines():
        match = re.match(r"^\s*(\d+)\s+(\d+)\s+(.*)$", line)
        if match is None:
            continue
        process_entries.append(
            ProcessEntry(
                process_id=int(match.group(1)),
                parent_process_id=int(match.group(2)),
                commandline=match.group(3).strip(),
            )
        )
    return _filter_process_entries(process_entries, root_pid=root_pid)


def _filter_process_entries(entries: list[ProcessEntry], root_pid: int | None = None) -> list[ProcessEntry]:
    if root_pid is None:
        return [entry for entry in entries if entry.commandline]
    descendant_ids = {root_pid}
    expanded = True
    while expanded:
        expanded = False
        for entry in entries:
            if entry.parent_process_id in descendant_ids and entry.process_id not in descendant_ids:
                descendant_ids.add(entry.process_id)
                expanded = True
    return [entry for entry in entries if entry.process_id in descendant_ids and entry.commandline]


def _extract_running_pizhi_commands(commandline: str) -> list[str]:
    normalized = " ".join(commandline.strip().split())
    if not normalized:
        return []
    commands: list[str] = []
    for match in re.finditer(r"(?i)-m\s+pizhi\s+(?P<tail>.+?)(?=(?:&&|\|\||;)|$)", normalized):
        tail = match.group("tail").strip()
        if tail:
            commands.append(tail)
    for match in re.finditer(
        r"(?i)(?:^|[\\/\s\"'])pizhi(?:\.exe)?(?:[\"']|\s)+(?P<tail>.+?)(?=(?:&&|\|\||;)|$)",
        normalized,
    ):
        tail = match.group("tail").strip()
        if tail:
            commands.append(tail)
    unique_commands: list[str] = []
    for command in commands:
        if command not in unique_commands:
            unique_commands.append(command)
    return unique_commands


def _is_allowed_running_pizhi_command(command: str, allowed_fragments: tuple[str, ...]) -> bool:
    normalized_command = _normalize_running_pizhi_command(command)
    return any(re.fullmatch(pattern, normalized_command) for pattern in allowed_fragments)


def _normalize_running_pizhi_command(command: str) -> str:
    normalized = " ".join(command.strip().split())
    for _ in range(2):
        normalized = re.sub(r"\s+<\s+(?:/dev/null|nul)\s*$", "", normalized, flags=re.IGNORECASE).strip()
        normalized = normalized.rstrip("'\"").strip()
    return normalized.lower()


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
    issues.extend(_load_blocked_session_issues(Path(project_root), target_end_chapter=target_chapters))

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
