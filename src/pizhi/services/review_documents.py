from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


SECTION_HEADING_RE = re.compile(r"^## (?P<name>.+?)\s*$", re.MULTILINE)
SUPPORTED_CHAPTER_REVIEW_HEADINGS = {
    "作者备注",
    "A 类结构检查",
    "B 类 AI 审查",
    "一致性检查结果",
}


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

    sections = _parse_supported_chapter_review_sections(raw)
    if sections is None:
        return ChapterReviewNotes(author_notes=raw, ai_review_markdown="")

    author_notes = sections.get("作者备注", "")
    if not author_notes:
        author_notes = sections.get("一致性检查结果", "")

    return ChapterReviewNotes(author_notes=author_notes, ai_review_markdown=sections.get("B 类 AI 审查", ""))


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
) -> None:
    sections = {
        "作者备注": author_notes,
        "A 类结构检查": structural_markdown,
        "B 类 AI 审查": ai_review_markdown,
    }
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
        content = raw[start:end]
        if name in sections:
            raise ValueError(f"duplicate section: {name}")
        sections[name] = content

    return sections


def _parse_supported_chapter_review_sections(raw: str) -> dict[str, str] | None:
    matches = list(SECTION_HEADING_RE.finditer(raw))
    if not matches:
        return None if raw.strip() else {}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group("name").strip()
        if name not in SUPPORTED_CHAPTER_REVIEW_HEADINGS:
            return None
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        content = raw[start:end]
        if name in sections:
            raise ValueError(f"duplicate section: {name}")
        sections[name] = content

    return sections
