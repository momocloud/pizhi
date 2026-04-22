from __future__ import annotations

from typing import Any

import yaml


import re


def _fix_yaml_scalar_quotes(yaml_text: str) -> str:
    # Fix list items where a quoted string is followed immediately by non-whitespace
    # e.g. - "foo"(bar) -> - '"foo"(bar)'
    # e.g. - 'foo'(bar) -> - "'foo'(bar)"
    lines = yaml_text.split("\n")
    fixed_lines: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("- "):
            content = stripped[2:]
            # Check if content starts with a double-quoted string that's not the full content
            match = re.match(r'^"([^"]*)"(\S.*)$', content)
            if match:
                prefix_spaces = len(line) - len(stripped)
                fixed_lines.append(" " * prefix_spaces + '- ' + repr(content))
                continue
            # Check if content starts with a single-quoted string that's not the full content
            match = re.match(r"^'([^']*)'(\S.*)$", content)
            if match:
                prefix_spaces = len(line) - len(stripped)
                fixed_lines.append(" " * prefix_spaces + '- ' + repr(content))
                continue
        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    if not raw.startswith("---\n"):
        raise ValueError("document must start with YAML frontmatter")

    marker = "\n---\n"
    end = raw.find(marker, 4)
    if end == -1:
        raise ValueError("frontmatter closing marker not found")

    metadata_block = raw[4:end]
    body = raw[end + len(marker) :]

    try:
        metadata = yaml.safe_load(metadata_block) or {}
    except yaml.YAMLError:
        metadata_block = _fix_yaml_scalar_quotes(metadata_block)
        metadata = yaml.safe_load(metadata_block) or {}

    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must decode to a mapping")
    return metadata, body
