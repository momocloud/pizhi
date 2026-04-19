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


def run_provider_configure(args: argparse.Namespace) -> int:
    paths = project_paths(Path.cwd())
    config = load_config(paths.config_file)
    existing = config.provider
    interactive_review = not _is_parameter_mode(args)
    provider_section = ProviderSection(
        provider=args.provider
        or _prompt_for_value("Provider", existing.provider if existing else None),
        model=args.model or _prompt_for_value("Model", existing.model if existing else None),
        base_url=args.base_url
        or _prompt_for_value("Base URL", existing.base_url if existing else None),
        api_key_env=args.api_key_env
        or _prompt_for_value("API key env", existing.api_key_env if existing else None),
        review_model=(
            args.review_model
            if args.review_model is not None
            else (
                _prompt_for_optional_value("Review model", existing.review_model if existing else None)
                if interactive_review
                else (existing.review_model if existing else None)
            )
        ),
        review_base_url=(
            args.review_base_url
            if args.review_base_url is not None
            else (
                _prompt_for_optional_value("Review base URL", existing.review_base_url if existing else None)
                if interactive_review
                else (existing.review_base_url if existing else None)
            )
        ),
        review_api_key_env=(
            args.review_api_key_env
            if args.review_api_key_env is not None
            else (
                _prompt_for_optional_value("Review API key env", existing.review_api_key_env if existing else None)
                if interactive_review
                else (existing.review_api_key_env if existing else None)
            )
        ),
    )
    config.provider = provider_section
    save_config(paths.config_file, config)
    print(f"Provider configured: {provider_section.provider} {provider_section.model}")
    return 0
