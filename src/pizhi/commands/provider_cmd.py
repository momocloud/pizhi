from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.paths import project_paths


def run_provider_configure(args: argparse.Namespace) -> int:
    paths = project_paths(Path.cwd())
    config = load_config(paths.config_file)
    provider_section = ProviderSection(
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
    )
    config.provider = provider_section
    save_config(paths.config_file, config)
    print(f"Provider configured: {provider_section.provider} {provider_section.model}")
    return 0
