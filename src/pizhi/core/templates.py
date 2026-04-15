from __future__ import annotations

from pathlib import Path


def initial_markdown_files(project_name: str, genre: str) -> dict[Path, str]:
    title_suffix = f" for {project_name}" if project_name else ""
    genre_line = f"Genre: {genre}\n\n" if genre else ""

    return {
        Path("global/synopsis.md"): f"# Synopsis{title_suffix}\n\n{genre_line}",
        Path("global/worldview.md"): "# Worldview\n\n",
        Path("global/timeline.md"): "# Timeline\n\n",
        Path("global/foreshadowing.md"): "# Foreshadowing Tracker\n\n## Active\n\n## Referenced\n\n## Resolved\n\n## Abandoned\n",
        Path("global/characters_index.md"): "# Characters Index\n\n",
        Path("global/outline_global.md"): "# Global Outline\n\n",
        Path("global/rules.md"): "# Rules\n\n",
        Path("chapters/ch000/characters.md"): "# Chapter 000 Characters\n\n",
        Path("chapters/ch000/relationships.md"): "# Chapter 000 Relationships\n\n",
        Path("hooks/pre_chapter.md"): "# Pre Chapter Checklist\n\n",
        Path("hooks/post_chapter.md"): "# Post Chapter Checklist\n\n",
        Path("hooks/consistency_check.md"): "# Consistency Check Template\n\n",
        Path("cache/last_session.md"): "# Last Session\n\n",
        Path("cache/pending_actions.md"): "# Pending Actions\n\n",
    }
