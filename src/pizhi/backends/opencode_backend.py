from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from pizhi.backends.agent_backend import AgentBackendArtifacts
from pizhi.backends.base import ExecutionRequest
from pizhi.backends.base import ExecutionResult
from pizhi.core.config import AgentBackendSection
from pizhi.core.paths import project_paths
from pizhi.services.agent_task_package import AGENT_NAME
from pizhi.services.agent_task_package import render_opencode_task_package
from pizhi.services.run_store import RunStore
from pizhi.services.write_candidate_validation import validate_write_candidate


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

        with tempfile.TemporaryDirectory(prefix="pizhi-opencode-") as temp_dir:
            workspace_dir = Path(temp_dir)
            package = render_opencode_task_package(
                workspace_dir,
                prompt_request=request.prompt_request,
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
