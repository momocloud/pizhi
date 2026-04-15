from __future__ import annotations

from typing import Any

import yaml


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    if not raw.startswith("---\n"):
        raise ValueError("document must start with YAML frontmatter")

    marker = "\n---\n"
    end = raw.find(marker, 4)
    if end == -1:
        raise ValueError("frontmatter closing marker not found")

    metadata_block = raw[4:end]
    body = raw[end + len(marker) :]
    metadata = yaml.safe_load(metadata_block) or {}
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must decode to a mapping")
    return metadata, body
