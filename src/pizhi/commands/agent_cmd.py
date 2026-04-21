from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from pizhi.core.config import AgentBackendSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.paths import project_paths


def _prompt_for_value(label: str, current_value: str | None = None) -> str:
    prompt = label
    if current_value:
        prompt += f" [{current_value}]"
    prompt += ": "

    while True:
        value = input(prompt).strip()
        if value:
            return value
        if current_value:
            return current_value
        print(f"{label} is required.")


def _prompt_for_args(current_args: list[str] | None) -> list[str]:
    current_value = " ".join(current_args or [])
    prompt = "Agent args"
    if current_value:
        prompt += f" [{current_value}]"
    prompt += " (leave blank to skip): "

    try:
        value = input(prompt).strip()
    except EOFError:
        return list(current_args or [])
    if not value:
        return list(current_args or [])
    return shlex.split(value)


def _is_parameter_mode(args: argparse.Namespace) -> bool:
    return args.agent_backend is not None and args.agent_command is not None


def run_agent_configure(args: argparse.Namespace) -> int:
    paths = project_paths(Path.cwd())
    config = load_config(paths.config_file)
    existing = config.execution.agent
    interactive = not _is_parameter_mode(args)

    agent_section = AgentBackendSection(
        agent_backend=args.agent_backend
        or _prompt_for_value(
            "Agent backend",
            existing.agent_backend if existing else "opencode",
        ),
        agent_command=args.agent_command
        or _prompt_for_value(
            "Agent command",
            existing.agent_command if existing else "opencode",
        ),
        agent_args=list(args.agent_args)
        if args.agent_args is not None
        else (_prompt_for_args(existing.agent_args if existing else None) if interactive else list(existing.agent_args if existing else [])),
    )

    config.execution.backend = "agent"
    config.execution.agent = agent_section
    save_config(paths.config_file, config)
    print(f"Agent backend configured: {agent_section.agent_backend} {agent_section.agent_command}")
    return 0
