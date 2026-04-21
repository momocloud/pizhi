from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from pizhi.adapters.base import PromptRequest


AGENT_NAME = "pizhi-step"


@dataclass(frozen=True, slots=True)
class AgentTaskPackage:
    workspace_dir: Path
    request_path: Path
    task_path: Path
    output_path: Path
    stdout_path: Path
    stderr_path: Path
    agent_file_path: Path

    @property
    def agent_path(self) -> Path:
        return self.agent_file_path


def render_agent_task_package(
    run_dir: Path,
    *,
    prompt_request: PromptRequest,
    target: str,
    backend_name: str,
    run_id: str | None = None,
) -> AgentTaskPackage:
    run_dir.mkdir(parents=True, exist_ok=True)
    request_path = run_dir / "agent_request.json"
    task_path = run_dir / "agent_task.md"
    output_path = run_dir / "agent_output.md"
    stdout_path = run_dir / "agent_stdout.txt"
    stderr_path = run_dir / "agent_stderr.txt"
    agent_file_path = run_dir / ".opencode" / "agents" / f"{AGENT_NAME}.md"
    agent_file_path.parent.mkdir(parents=True, exist_ok=True)

    bridge_files = {
        "request": request_path.name,
        "task": task_path.name,
        "output": output_path.name,
        "stdout": stdout_path.name,
        "stderr": stderr_path.name,
        "agent": str(Path(".opencode") / "agents" / agent_file_path.name).replace("\\", "/"),
    }
    request_payload = {
        "run_id": run_id,
        "backend": backend_name,
        "command": prompt_request.command_name,
        "target": target,
        "metadata": prompt_request.metadata,
        "referenced_files": prompt_request.referenced_files,
        "bridge_files": bridge_files,
        "output_file": output_path.name,
    }
    request_path.write_text(
        json.dumps(request_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    task_path.write_text(
        _render_task_markdown(prompt_request, target=target, output_file=output_path.name),
        encoding="utf-8",
        newline="\n",
    )
    agent_file_path.write_text(
        _render_agent_markdown(output_file=output_path.name),
        encoding="utf-8",
        newline="\n",
    )
    return AgentTaskPackage(
        workspace_dir=run_dir,
        request_path=request_path,
        task_path=task_path,
        output_path=output_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        agent_file_path=agent_file_path,
    )


def render_opencode_task_package(
    workspace_dir: Path,
    *,
    prompt_request: PromptRequest,
    run_id: str,
    target: str,
) -> AgentTaskPackage:
    return render_agent_task_package(
        workspace_dir,
        prompt_request=prompt_request,
        target=target,
        backend_name="opencode",
        run_id=run_id,
    )


def _render_task_markdown(prompt_request: PromptRequest, *, target: str, output_file: str) -> str:
    lines = [
        "# Pizhi Step Task",
        "",
        f"- Command: {prompt_request.command_name}",
        f"- Target: {target}",
        f"- Output file: `{output_file}`",
        "",
        "## Required behavior",
        "",
        f"1. Read this task and write the final candidate result to `{output_file}`.",
        "2. Do not modify project source-of-truth files or `.pizhi/`.",
        "3. Do not use stdout or stderr as the result channel.",
        "",
    ]
    if prompt_request.command_name == "write":
        lines.extend(
            [
                "For `write`, preserve the exact chapter response contract from the prompt.",
                "Start the candidate with YAML frontmatter delimited by `---`.",
                "`timeline_events` must stay a YAML list of objects.",
                "`foreshadowing` must stay a YAML object with `introduced`, `referenced`, and `resolved` lists.",
                "The candidate must include `## characters_snapshot` and `## relationships_snapshot`.",
                "Do not add commentary before or after the candidate.",
                "",
            ]
        )
    lines.extend(
        [
            "## Prompt",
            "",
            prompt_request.prompt_text.rstrip(),
            "",
        ]
    )
    return "\n".join(lines)


def _render_agent_markdown(*, output_file: str) -> str:
    return "\n".join(
        [
            "---",
            "name: pizhi-step",
            "description: Temporary one-run Pizhi execution agent.",
            "---",
            "You are a temporary Pizhi step execution agent.",
            "",
            "Rules:",
            f"- Read `agent_task.md` and write the final candidate result only to `{output_file}`.",
            "- `agent_output.md` is the only result handoff file.",
            "- Do not modify project source-of-truth files, `manuscript/`, or `.pizhi/`.",
            "- Keep stdout and stderr incidental audit channels only.",
            "- If the task is a `write` step, keep the exact chapter response contract intact.",
            "- Never replace the structured chapter response with free-form prose.",
            "- Do not collapse `timeline_events` into prose bullets or `foreshadowing` into a flat list.",
            "",
        ]
    )
