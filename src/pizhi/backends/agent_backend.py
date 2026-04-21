from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentBackendArtifacts:
    backend_name: str
    output_file: str = "agent_output.md"
    stdout_file: str = "agent_stdout.txt"
    stderr_file: str = "agent_stderr.txt"
