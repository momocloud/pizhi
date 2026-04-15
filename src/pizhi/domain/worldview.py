from __future__ import annotations

import re


PATCH_SECTION_RE = re.compile(
    r"^## (?P<name>Added|Modified|Retracted)\s*$\n(?P<content>.*?)(?=^## (?:Added|Modified|Retracted)\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)
TITLE_RE = re.compile(r"\*\*(?P<title>.+?)\*\*")


def apply_worldview_patch(current_text: str, patch_text: str) -> str:
    sections = _parse_patch_sections(patch_text)
    lines = current_text.rstrip("\n").splitlines()
    if not lines:
        lines = ["# Worldview"]

    for item in sections["Modified"]:
        lines = _replace_item(lines, item)
    for item in sections["Retracted"]:
        lines = _remove_item(lines, item)
    for item in sections["Added"]:
        lines.append(item)

    return "\n".join(lines).rstrip() + "\n"


def _parse_patch_sections(patch_text: str) -> dict[str, list[str]]:
    parsed = {"Added": [], "Modified": [], "Retracted": []}
    for match in PATCH_SECTION_RE.finditer(patch_text):
        items = []
        for line in match.group("content").splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and "（无）" not in stripped:
                items.append(stripped)
        parsed[match.group("name")] = items
    return parsed


def _replace_item(lines: list[str], new_item: str) -> list[str]:
    title = _extract_title(new_item)
    matched = [index for index, line in enumerate(lines) if _extract_title(line) == title]
    if len(matched) != 1:
        raise ValueError(f"worldview title match count for {title!r} was {len(matched)}")
    lines[matched[0]] = new_item
    return lines


def _remove_item(lines: list[str], item: str) -> list[str]:
    title = _extract_title(item)
    matched = [index for index, line in enumerate(lines) if _extract_title(line) == title]
    if len(matched) != 1:
        raise ValueError(f"worldview title match count for {title!r} was {len(matched)}")
    del lines[matched[0]]
    return lines


def _extract_title(line: str) -> str | None:
    match = TITLE_RE.search(line)
    return match.group("title") if match else None
