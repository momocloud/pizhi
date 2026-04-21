from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.paths import project_paths


def _prompt_for_value(label: str, current_value: str | None = None) -> str:
    prompt = f"{label}"
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


def _prompt_for_optional_value(label: str, current_value: str | None = None) -> str | None:
    prompt = f"{label}"
    if current_value:
        prompt += f" [{current_value}]"
    prompt += " (leave blank to skip): "

    while True:
        try:
            value = input(prompt).strip()
        except EOFError:
            return current_value
        if value:
            return value
        return current_value


def _is_parameter_mode(args: argparse.Namespace) -> bool:
    return all(
        getattr(args, field) is not None
        for field in ("provider", "model", "base_url", "api_key_env")
    )


def _resolve_optional_value(
    args: argparse.Namespace,
    field_name: str,
    label: str,
    *,
    existing_value: str | None,
    interactive: bool,
) -> str | None:
    value = getattr(args, field_name)
    if value is not None:
        return value
    if interactive:
        return _prompt_for_optional_value(label, existing_value)
    return existing_value


def run_provider_configure(args: argparse.Namespace) -> int:
    paths = project_paths(Path.cwd())
    config = load_config(paths.config_file)
    existing = config.execution.provider
    interactive_review = not _is_parameter_mode(args)
    provider_section = ProviderSection(
        provider=args.provider
        or _prompt_for_value("Provider", existing.provider if existing else None),
        model=args.model or _prompt_for_value("Model", existing.model if existing else None),
        base_url=args.base_url
        or _prompt_for_value("Base URL", existing.base_url if existing else None),
        api_key_env=args.api_key_env
        or _prompt_for_value("API key env", existing.api_key_env if existing else None),
        brainstorm_model=_resolve_optional_value(
            args,
            "brainstorm_model",
            "Brainstorm model",
            existing_value=existing.brainstorm_model if existing else None,
            interactive=interactive_review,
        ),
        outline_model=_resolve_optional_value(
            args,
            "outline_model",
            "Outline model",
            existing_value=existing.outline_model if existing else None,
            interactive=interactive_review,
        ),
        write_model=_resolve_optional_value(
            args,
            "write_model",
            "Write model",
            existing_value=existing.write_model if existing else None,
            interactive=interactive_review,
        ),
        continue_model=_resolve_optional_value(
            args,
            "continue_model",
            "Continue model",
            existing_value=existing.continue_model if existing else None,
            interactive=interactive_review,
        ),
        review_model=_resolve_optional_value(
            args,
            "review_model",
            "Review model",
            existing_value=existing.review_model if existing else None,
            interactive=interactive_review,
        ),
        review_base_url=_resolve_optional_value(
            args,
            "review_base_url",
            "Review base URL",
            existing_value=existing.review_base_url if existing else None,
            interactive=interactive_review,
        ),
        review_api_key_env=_resolve_optional_value(
            args,
            "review_api_key_env",
            "Review API key env",
            existing_value=existing.review_api_key_env if existing else None,
            interactive=interactive_review,
        ),
    )
    config.execution.backend = "provider"
    config.execution.provider = provider_section
    save_config(paths.config_file, config)
    print(f"Provider configured: {provider_section.provider} {provider_section.model}")
    return 0
