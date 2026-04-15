from __future__ import annotations

from dataclasses import dataclass
import re


SECTION_PATTERN = re.compile(
    r"^## (?P<name>[a-z_]+)\s*$\n(?P<content>.*?)(?=^## [a-z_]+\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass(slots=True)
class ChapterSections:
    body: str
    characters_snapshot: str
    relationships_snapshot: str
    worldview_patch: str | None
    synopsis_new: str | None


def split_chapter_sections(raw: str) -> ChapterSections:
    first_section = SECTION_PATTERN.search(raw)
    if first_section is None:
        raise ValueError("chapter document is missing named sections")

    body = raw[: first_section.start()].strip()
    sections = {
        match.group("name"): match.group("content").strip()
        for match in SECTION_PATTERN.finditer(raw)
    }

    if "characters_snapshot" not in sections:
        raise ValueError("missing characters_snapshot section")
    if "relationships_snapshot" not in sections:
        raise ValueError("missing relationships_snapshot section")

    return ChapterSections(
        body=body,
        characters_snapshot=sections["characters_snapshot"],
        relationships_snapshot=sections["relationships_snapshot"],
        worldview_patch=sections.get("worldview_patch"),
        synopsis_new=sections.get("synopsis_new"),
    )
