from __future__ import annotations

from typing import Any

import yaml

import re


def _fix_single_quoted_backslash_apostrophes(yaml_text: str) -> str:
    fixed_lines: list[str] = []
    for line in yaml_text.split("\n"):
        fixed_chars: list[str] = []
        in_single_quoted_scalar = False
        index = 0
        while index < len(line):
            char = line[index]
            next_char = line[index + 1] if index + 1 < len(line) else ""
            if char == "'":
                if in_single_quoted_scalar and next_char == "'":
                    fixed_chars.append("''")
                    index += 2
                    continue
                in_single_quoted_scalar = not in_single_quoted_scalar
                fixed_chars.append(char)
                index += 1
                continue
            if in_single_quoted_scalar and char == "\\" and next_char == "'":
                fixed_chars.append("''")
                index += 2
                continue
            fixed_chars.append(char)
            index += 1
        fixed_lines.append("".join(fixed_chars))
    return "\n".join(fixed_lines)


def _escape_lone_single_quotes(value: str) -> str:
    fixed_chars: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        next_char = value[index + 1] if index + 1 < len(value) else ""
        if char == "'":
            if next_char == "'":
                fixed_chars.append("''")
                index += 2
                continue
            fixed_chars.append("''")
            index += 1
            continue
        fixed_chars.append(char)
        index += 1
    return "".join(fixed_chars)


def _fix_plain_apostrophes_in_single_quoted_scalars(yaml_text: str) -> str:
    fixed_lines: list[str] = []
    for line in yaml_text.split("\n"):
        match = re.match(r"^(\s*(?:-\s*)?[^:]+:\s*)'(.*)'(\s*)$", line)
        if not match:
            fixed_lines.append(line)
            continue
        prefix, value, suffix = match.groups()
        fixed_lines.append(f"{prefix}'{_escape_lone_single_quotes(value)}'{suffix}")
    return "\n".join(fixed_lines)


def _fix_yaml_scalar_quotes(yaml_text: str) -> str:
    # Fix list items where a quoted string is followed immediately by non-whitespace
    # e.g. - "foo"(bar) -> - '"foo"(bar)'
    # e.g. - 'foo'(bar) -> - "'foo'(bar)"
    # e.g. key: "foo"bar -> key: '"foo"bar'
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
        match = re.match(r"^(\s*(?:-\s*)?[^:]+:\s*)(\"[^\"]*\"(?!\")|'(?:[^']|'')*'(?!'))(\S.*)$", line)
        if match:
            prefix, quoted_prefix, suffix = match.groups()
            fixed_lines.append(prefix + repr(quoted_prefix + suffix))
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
        metadata_block = _fix_single_quoted_backslash_apostrophes(metadata_block)
        metadata_block = _fix_plain_apostrophes_in_single_quoted_scalars(metadata_block)
        metadata_block = _fix_yaml_scalar_quotes(metadata_block)
        metadata = yaml.safe_load(metadata_block) or {}

    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must decode to a mapping")
    return metadata, body
