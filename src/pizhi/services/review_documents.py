from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pizhi.services.agent_extensions import ExtensionReportSection


SECTION_HEADING_RE = re.compile(r"^## (?P<name>.+?)\s*$", re.MULTILINE)
SUPPORTED_CHAPTER_REVIEW_HEADINGS = {
    "作者备注",
    "A 类结构检查",
    "B 类 AI 审查",
    "一致性检查结果",
}
FULL_REVIEW_TITLE = "# Review Full"
REVIEW_AGENT_SECTION_PREFIX = "Review Agent "


@dataclass(frozen=True, slots=True)
class ChapterReviewNotes:
    author_notes: str
    ai_review_markdown: str


def load_chapter_review_notes(path: Path) -> ChapterReviewNotes:
    if not path.exists():
        return ChapterReviewNotes(author_notes="", ai_review_markdown="")

    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return ChapterReviewNotes(author_notes="", ai_review_markdown="")

    return _parse_chapter_review_notes(raw)


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

    chunks: list[str] = []
    for index, name in enumerate(ordered_names):
        if index > 0:
            chunks.append("\n")
        chunks.append(f"## {name}\n\n")
        chunks.append(sections.get(name, ""))
    content = "".join(chunks)
    if not content.endswith("\n"):
        content += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_chapter_review_notes(
    path: Path,
    *,
    author_notes: str,
    structural_markdown: str,
    ai_review_markdown: str,
    extension_sections: list[ExtensionReportSection] | None = None,
) -> None:
    sections = {
        "作者备注": author_notes,
        "A 类结构检查": structural_markdown,
        "B 类 AI 审查": ai_review_markdown,
        **{section.title: section.body for section in extension_sections or []},
    }
    section_order = [
        "作者备注",
        "A 类结构检查",
        "B 类 AI 审查",
        *[section.title for section in extension_sections or []],
    ]
    write_sectioned_markdown(path, sections, section_order=section_order)


def write_full_review_document(
    path: Path,
    *,
    summary_markdown: str,
    structural_markdown: str,
    maintenance_markdown: str,
    ai_review_markdown: str,
    extension_sections: list[ExtensionReportSection] | None = None,
) -> None:
    chunks = [
        f"{FULL_REVIEW_TITLE}\n\n",
        "## Summary\n\n",
        _normalize_section_body(summary_markdown),
        "\n## A 类结构检查\n\n",
        _normalize_section_body(structural_markdown),
        "\n## Maintenance\n\n",
        _normalize_section_body(maintenance_markdown),
        "\n## B 类 AI 审查\n\n",
        _normalize_section_body(ai_review_markdown),
    ]
    for section in extension_sections or []:
        chunks.extend(
            [
                f"\n## {section.title}\n\n",
                _normalize_section_body(section.body),
            ]
        )
    content = "".join(chunks)
    if not content.endswith("\n"):
        content += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


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
        content = raw[start:end]
        if name in sections:
            raise ValueError(f"duplicate section: {name}")
        sections[name] = content

    return sections


def _parse_chapter_review_notes(raw: str) -> ChapterReviewNotes:
    matches = list(SECTION_HEADING_RE.finditer(raw))
    if not matches:
        return ChapterReviewNotes(author_notes=raw, ai_review_markdown="")

    headings = [match.group("name").strip() for match in matches]
    supported_headings = [name for name in headings if _is_machine_managed_chapter_heading(name)]
    if not supported_headings:
        return ChapterReviewNotes(author_notes=raw, ai_review_markdown="")

    prefix = raw[: matches[0].start()]
    sections: dict[str, str] = {}
    author_parts: list[str] = [prefix]
    ai_review_markdown = ""

    for index, match in enumerate(matches):
        name = match.group("name").strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        content = raw[start:end]
        if name in sections:
            if name == "作者备注":
                author_parts.append(content)
                continue
            if name in {"A 类结构检查", "B 类 AI 审查", "一致性检查结果"}:
                author_parts.append(raw[match.start():end])
            if name == "B 类 AI 审查":
                ai_review_markdown = content
            elif not _is_machine_managed_chapter_heading(name):
                author_parts.append(raw[match.start():end])
            continue
        sections[name] = content

        if name == "作者备注":
            author_parts.append(content)
        elif name == "B 类 AI 审查":
            ai_review_markdown = content
        elif name == "一致性检查结果":
            continue
        elif _is_machine_managed_chapter_heading(name):
            continue
        else:
            author_parts.append(raw[match.start():end])

    if len(supported_headings) == len(headings):
        author_notes = "".join(author_parts)
    else:
        author_notes = "".join(author_parts)
        # Unknown headings have already been appended verbatim above.

    return ChapterReviewNotes(author_notes=author_notes, ai_review_markdown=ai_review_markdown)


def _normalize_section_body(text: str) -> str:
    stripped = text.rstrip()
    if not stripped:
        return "\n"
    return stripped + "\n"


def _is_machine_managed_chapter_heading(name: str) -> bool:
    return name in SUPPORTED_CHAPTER_REVIEW_HEADINGS or name.startswith(REVIEW_AGENT_SECTION_PREFIX)
