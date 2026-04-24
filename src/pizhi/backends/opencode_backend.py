from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from pizhi.adapters.base import PromptRequest
from pizhi.backends.agent_backend import AgentBackendArtifacts
from pizhi.backends.base import ExecutionRequest
from pizhi.backends.base import ExecutionResult
from pizhi.core.config import AgentBackendSection
from pizhi.core.paths import project_paths
from pizhi.services.agent_task_package import AGENT_NAME
from pizhi.services.agent_task_package import render_opencode_task_package
from pizhi.services.run_store import RunStore
from pizhi.services.write_candidate_validation import validate_write_candidate

_REPAIR_OUTPUT_FILE = "repair_output.md"
_REPAIR_TASK_FILE = "repair_task.md"
_REPAIR_STDOUT_FILE = "repair_stdout.txt"
_REPAIR_STDERR_FILE = "repair_stderr.txt"


class OpencodeExecutionBackend:
    backend_name = "agent"

    def __init__(self) -> None:
        self.artifacts = AgentBackendArtifacts(backend_name="opencode")

    def execute(
        self,
        request: ExecutionRequest,
        *,
        backend_config: object | None = None,
    ) -> ExecutionResult:
        if not isinstance(backend_config, AgentBackendSection):
            raise TypeError("agent backend override must be an AgentBackendSection")
        if backend_config.agent_backend != "opencode":
            raise ValueError(f"unsupported agent backend: {backend_config.agent_backend}")

        store = RunStore(project_paths(request.project_root).runs_dir)
        run_id = store.new_run_id()

        resolved_request = PromptRequest(
            command_name=request.prompt_request.command_name,
            prompt_text=request.prompt_request.prompt_text,
            metadata=request.prompt_request.metadata,
            referenced_files=[
                str((request.project_root / path).resolve())
                for path in request.prompt_request.referenced_files
            ],
        )

        with tempfile.TemporaryDirectory(prefix="pizhi-opencode-") as temp_dir:
            workspace_dir = Path(temp_dir)
            package = render_opencode_task_package(
                workspace_dir,
                prompt_request=resolved_request,
                run_id=run_id,
                target=request.target,
            )
            command = _build_command(backend_config, package, run_id=run_id)
            completed = subprocess.run(
                command,
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            package.stdout_path.write_text(completed.stdout or "", encoding="utf-8", newline="\n")
            package.stderr_path.write_text(completed.stderr or "", encoding="utf-8", newline="\n")

            output_text = package.output_path.read_text(encoding="utf-8") if package.output_path.exists() else None
            metadata = {
                **request.prompt_request.metadata,
                "backend": self.backend_name,
                "agent_backend": backend_config.agent_backend,
                "agent_command": backend_config.agent_command,
                "agent_args": list(backend_config.agent_args),
                "agent_name": AGENT_NAME,
            }
            raw_payload = {
                "backend": self.backend_name,
                "agent_backend": backend_config.agent_backend,
                "command": command,
                "returncode": completed.returncode,
                "stdout_path": self.artifacts.stdout_file,
                "stderr_path": self.artifacts.stderr_file,
                "agent_output_path": self.artifacts.output_file,
            }
            extra_files = _collect_extra_files(package)

            if completed.returncode != 0:
                record = store.write_failure(
                    run_id=run_id,
                    command=request.prompt_request.command_name,
                    target=request.target,
                    prompt_text=request.prompt_request.prompt_text,
                    raw_payload=raw_payload,
                    normalized_text=output_text,
                    error_text=(completed.stderr or "").strip() or f"opencode exited with code {completed.returncode}",
                    status="agent_failed",
                    metadata=metadata,
                    referenced_files=request.prompt_request.referenced_files,
                    extra_files=extra_files,
                )
                return ExecutionResult(run_id=record.run_id, run_dir=record.run_dir, status="agent_failed", record=record)

            if output_text is None:
                record = store.write_failure(
                    run_id=run_id,
                    command=request.prompt_request.command_name,
                    target=request.target,
                    prompt_text=request.prompt_request.prompt_text,
                    raw_payload=raw_payload,
                    error_text="agent output file was not produced",
                    status="normalize_failed",
                    metadata=metadata,
                    referenced_files=request.prompt_request.referenced_files,
                    extra_files=extra_files,
                )
                return ExecutionResult(run_id=record.run_id, run_dir=record.run_dir, status="normalize_failed", record=record)

            if not output_text.strip():
                record = store.write_failure(
                    run_id=run_id,
                    command=request.prompt_request.command_name,
                    target=request.target,
                    prompt_text=request.prompt_request.prompt_text,
                    raw_payload=raw_payload,
                    normalized_text=output_text,
                    error_text="agent output file was empty",
                    status="normalize_failed",
                    metadata=metadata,
                    referenced_files=request.prompt_request.referenced_files,
                    extra_files=extra_files,
                )
                return ExecutionResult(run_id=record.run_id, run_dir=record.run_dir, status="normalize_failed", record=record)

            if request.prompt_request.command_name == "write":
                try:
                    validate_write_candidate(output_text)
                except ValueError as exc:
                    repaired_output, repair_files = self._repair_write_candidate(
                        workspace_dir=workspace_dir,
                        backend_config=backend_config,
                        run_id=run_id,
                        original_output=output_text,
                        validation_error=str(exc),
                    )
                    extra_files.update(repair_files)
                    if repaired_output is not None:
                        try:
                            validate_write_candidate(repaired_output)
                        except ValueError as repair_exc:
                            record = store.write_failure(
                                run_id=run_id,
                                command=request.prompt_request.command_name,
                                target=request.target,
                                prompt_text=request.prompt_request.prompt_text,
                                raw_payload=raw_payload,
                                normalized_text=repaired_output,
                                error_text=str(repair_exc),
                                status="normalize_failed",
                                metadata=metadata,
                                referenced_files=request.prompt_request.referenced_files,
                                extra_files=extra_files,
                            )
                            return ExecutionResult(
                                run_id=record.run_id,
                                run_dir=record.run_dir,
                                status="normalize_failed",
                                record=record,
                            )
                        output_text = repaired_output
                    else:
                        record = store.write_failure(
                            run_id=run_id,
                            command=request.prompt_request.command_name,
                            target=request.target,
                            prompt_text=request.prompt_request.prompt_text,
                            raw_payload=raw_payload,
                            normalized_text=output_text,
                            error_text=str(exc),
                            status="normalize_failed",
                            metadata=metadata,
                            referenced_files=request.prompt_request.referenced_files,
                            extra_files=extra_files,
                        )
                        return ExecutionResult(
                            run_id=record.run_id,
                            run_dir=record.run_dir,
                            status="normalize_failed",
                            record=record,
                        )

            record = store.write_success(
                run_id=run_id,
                command=request.prompt_request.command_name,
                target=request.target,
                prompt_text=request.prompt_request.prompt_text,
                raw_payload=raw_payload,
                normalized_text=output_text,
                metadata=metadata,
                referenced_files=request.prompt_request.referenced_files,
                extra_files=extra_files,
            )
            return ExecutionResult(run_id=record.run_id, run_dir=record.run_dir, status="succeeded", record=record)

    def _repair_write_candidate(
        self,
        *,
        workspace_dir: Path,
        backend_config: AgentBackendSection,
        run_id: str,
        original_output: str,
        validation_error: str,
    ) -> tuple[str | None, dict[str, str]]:
        repair_task_path = workspace_dir / _REPAIR_TASK_FILE
        repair_output_path = workspace_dir / _REPAIR_OUTPUT_FILE
        repair_stdout_path = workspace_dir / _REPAIR_STDOUT_FILE
        repair_stderr_path = workspace_dir / _REPAIR_STDERR_FILE
        repair_task_path.write_text(
            _render_repair_task_markdown(
                original_output=original_output,
                validation_error=validation_error,
                output_file=repair_output_path.name,
            ),
            encoding="utf-8",
            newline="\n",
        )
        command = _build_command(
            backend_config,
            type(
                "RepairPackage",
                (),
                {
                    "workspace_dir": workspace_dir,
                    "task_path": repair_task_path,
                    "request_path": workspace_dir / "agent_request.json",
                    "output_path": repair_output_path,
                },
            )(),
            run_id=f"{run_id}-repair",
        )
        completed = subprocess.run(
            command,
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        repair_stdout_path.write_text(completed.stdout or "", encoding="utf-8", newline="\n")
        repair_stderr_path.write_text(completed.stderr or "", encoding="utf-8", newline="\n")
        extra_files = {
            _REPAIR_TASK_FILE: repair_task_path.read_text(encoding="utf-8"),
            _REPAIR_STDOUT_FILE: repair_stdout_path.read_text(encoding="utf-8"),
            _REPAIR_STDERR_FILE: repair_stderr_path.read_text(encoding="utf-8"),
        }
        if completed.returncode != 0 or not repair_output_path.exists():
            return None, extra_files
        repaired_output = repair_output_path.read_text(encoding="utf-8")
        extra_files[_REPAIR_OUTPUT_FILE] = repaired_output
        return repaired_output, extra_files


def _build_command(backend_config: AgentBackendSection, package, *, run_id: str) -> list[str]:
    command = [backend_config.agent_command]
    if backend_config.agent_args:
        command.extend(backend_config.agent_args)
    if command[1:2] != ["run"]:
        command.append("run")
    command.extend(
        [
            "--pure",
            "--dir",
            str(package.workspace_dir),
            "--agent",
            AGENT_NAME,
            "--format",
            "json",
            "--file",
            str(package.task_path),
            "--file",
            str(package.request_path),
            "--title",
            f"pizhi:{run_id}",
            f"Read the attached files and write the final candidate result to {package.output_path.name}.",
        ]
    )
    return command


def _collect_extra_files(package) -> dict[str, str]:
    files = {
        "agent_request.json": package.request_path.read_text(encoding="utf-8"),
        "agent_task.md": package.task_path.read_text(encoding="utf-8"),
        "agent_stdout.txt": package.stdout_path.read_text(encoding="utf-8"),
        "agent_stderr.txt": package.stderr_path.read_text(encoding="utf-8"),
        str(Path(".opencode") / "agents" / package.agent_path.name): package.agent_path.read_text(encoding="utf-8"),
    }
    if package.output_path.exists():
        files["agent_output.md"] = package.output_path.read_text(encoding="utf-8")
    return files


def _render_repair_task_markdown(*, original_output: str, validation_error: str, output_file: str) -> str:
    return "\n".join(
        [
            "# Pizhi Write Repair Task",
            "",
            f"- Output file: `{output_file}`",
            "",
            "## Required behavior",
            "",
            "1. Repair only formatting and schema issues in the failed write candidate.",
            "2. Do not change plot facts, character identities, events, or foreshadowing intent.",
            "3. Do not add or remove story beats beyond what is required to restore valid structure.",
            "4. Preserve the narrative body and section headings whenever possible.",
            "5. If you cannot repair the candidate without changing its meaning, copy it as-is.",
            "6. Do not put `worldview_patch` or `synopsis_new` in YAML frontmatter.",
            "7. When `worldview_changed: true`, add a Markdown section named `## worldview_patch` after the narrative body.",
            "8. When `synopsis_changed: true`, add a Markdown section named `## synopsis_new` after the narrative body.",
            "9. Keep required Markdown sections as `## characters_snapshot`, `## relationships_snapshot`, "
            "`## worldview_patch`, and `## synopsis_new` headings.",
            "",
            "## Validation error",
            "",
            validation_error,
            "",
            "## Failed candidate",
            "",
            original_output.rstrip(),
            "",
        ]
    )
