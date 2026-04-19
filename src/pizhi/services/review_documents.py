from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import re


SECTION_HEADING_RE = re.compile(r"^## (?P<name>.+?)\s*$", re.MULTILINE)


def load_sectioned_markdown(path: Path, required: Iterable[str]) -> dict[str, str]:
    sections = _parse_sectioned_markdown(path.read_text(encoding="utf-8")) if path.exists() else {}
    for name in required:
        sections.setdefault(name, "")
    return sections


def write_sectioned_markdown(path: Path, sections: dict[str, str], *, section_order: list[str]) -> None:
    ordered_names: list[str] = []
    seen: set[str] = set()

    for name in section_order:
        if name not in seen:
            ordered_names.append(name)
            seen.add(name)

    for name in sections:
        if name not in seen:
            ordered_names.append(name)
            seen.add(name)

    lines: list[str] = []
    for name in ordered_names:
        content = sections.get(name, "").strip()
        lines.append(f"## {name}")
        lines.append("")
        if content:
            lines.append(content)
            lines.append("")
        else:
            lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


def write_chapter_review_notes(path: Path, *, structural_markdown: str, ai_review_markdown: str) -> None:
    sections = load_sectioned_markdown(path, required=["作者备注", "A 类结构检查", "B 类 AI 审查"])
    sections["A 类结构检查"] = structural_markdown
    sections["B 类 AI 审查"] = ai_review_markdown
    write_sectioned_markdown(path, sections, section_order=["作者备注", "A 类结构检查", "B 类 AI 审查"])


def _parse_sectioned_markdown(raw: str) -> dict[str, str]:
    matches = list(SECTION_HEADING_RE.finditer(raw))
    if not matches:
        if raw.strip():
            raise ValueError("sectioned markdown is missing headings")
        return {}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group("name").strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        content = raw[start:end].strip()
        if name in sections:
            raise ValueError(f"duplicate section: {name}")
        sections[name] = content

    return sections

