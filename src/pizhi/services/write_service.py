from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.adapters.base import PromptArtifact
from pizhi.adapters.base import PromptRequest
from pizhi.adapters.prompt_only import PromptOnlyAdapter
from pizhi.services.chapter_context import ChapterContext
from pizhi.services.chapter_context import build_chapter_context
from pizhi.services.chapter_writer import ChapterWriteResult
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.maintenance import run_after_write
from pizhi.services.project_snapshot import load_project_snapshot


@dataclass(frozen=True, slots=True)
class WriteResult:
    prompt_artifact: PromptArtifact
    chapter_result: ChapterWriteResult | None
    maintenance_result: MaintenanceResult | None


@dataclass(frozen=True, slots=True)
class SynopsisCoveragePromptContext:
    foreshadowing_ids: tuple[str, ...]
    major_turning_points: tuple[str, ...]
    archived_major_turning_points: tuple[str, ...]


class WriteService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.adapter = PromptOnlyAdapter(project_root)
        self._last_maintenance_result: MaintenanceResult | None = None

    def build_prompt_request(self, chapter_number: int) -> PromptRequest:
        context = build_chapter_context(self.project_root, chapter_number)
        synopsis_coverage = _load_synopsis_coverage_prompt_context(self.project_root)
        return PromptRequest(
            command_name="write",
            prompt_text=_build_prompt(context, synopsis_coverage),
            metadata={"chapter": chapter_number},
            referenced_files=[
                ".pizhi/global/synopsis.md",
                ".pizhi/global/worldview.md",
                ".pizhi/global/rules.md",
                ".pizhi/global/foreshadowing.md",
                f".pizhi/chapters/ch{chapter_number:03d}/outline.md",
            ],
        )

    def prepare_prompt(self, request: PromptRequest) -> PromptArtifact:
        return self.adapter.prepare(request)

    def apply_response(self, chapter_number: int, raw_response: str) -> ChapterWriteResult:
        chapter_result = apply_chapter_response(
            self.project_root,
            chapter_number=chapter_number,
            raw_response=raw_response,
        )
        self._last_maintenance_result = run_after_write(self.project_root)
        return chapter_result

    def write(self, chapter_number: int, response_file: Path | None = None) -> WriteResult:
        artifact = self.prepare_prompt(self.build_prompt_request(chapter_number))

        chapter_result = None
        maintenance_result = None
        if response_file is not None:
            self._last_maintenance_result = None
            chapter_result = self.apply_response(
                chapter_number=chapter_number,
                raw_response=response_file.read_text(encoding="utf-8"),
            )
            maintenance_result = self._last_maintenance_result

        return WriteResult(
            prompt_artifact=artifact,
            chapter_result=chapter_result,
            maintenance_result=maintenance_result,
        )


def _build_prompt(context: ChapterContext, synopsis_coverage: SynopsisCoveragePromptContext) -> str:
    sections = [f"# Chapter Write Request\n\nChapter: {context.chapter_number}"]
    sections.append(_render_synopsis_response_contract(context.chapter_number))
    sections.append(_render_synopsis_coverage_requirements(synopsis_coverage))
    for name, content in context.required_inputs.items():
        sections.append(f"## {name}\n{content}")
    for name, content in context.optional_inputs.items():
        if content:
            sections.append(f"## {name}\n{content}")
    return "\n\n".join(sections).strip() + "\n"


def _load_synopsis_coverage_prompt_context(project_root: Path) -> SynopsisCoveragePromptContext:
    snapshot = load_project_snapshot(project_root)
    live_major_turning_point_ids = {
        entry.event_id for entry in snapshot.timeline_entries if entry.is_major_turning_point
    }
    major_turning_points = _ordered_unique(entry.event_id for entry in snapshot.major_turning_points)
    archived_major_turning_points = tuple(
        event_id for event_id in major_turning_points if event_id not in live_major_turning_point_ids
    )
    return SynopsisCoveragePromptContext(
        foreshadowing_ids=_ordered_unique(entry.entry_id for entry in snapshot.active_or_referenced_foreshadowing),
        major_turning_points=major_turning_points,
        archived_major_turning_points=archived_major_turning_points,
    )


def _render_synopsis_response_contract(chapter_number: int) -> str:
    chapter_prefix = f"T{chapter_number:03d}-"
    return (
        "## synopsis_response_contract\n"
        "Only include the synopsis update block when `synopsis_changed: true`.\n"
        "If `synopsis_changed: false`, omit both `## synopsis_new` and `## coverage_markers`.\n"
        "When `synopsis_changed: true`, append this exact optional block at the end of the response:\n\n"
        "## synopsis_new\n"
        "# Synopsis\n"
        "<updated synopsis body>\n\n"
        "## coverage_markers\n"
        "foreshadowing_ids:\n"
        "- <required foreshadowing id>\n"
        "major_turning_points:\n"
        "- <required major turning point id>\n\n"
        "`coverage_markers` must enumerate every required foreshadowing id and every required major turning point id, "
        "including trusted archived timeline turning points.\n"
        "If the pre-write lists below show `- (none)`, that only means no IDs were required before this write.\n"
        "You must still list every foreshadowing ID newly introduced or newly referenced in this chapter if it remains "
        "tracked after writing.\n"
        "You must also list every major turning point generated by this chapter's `timeline_events`.\n"
        f"For this chapter, timeline event #1 is `{chapter_prefix}01`, event #2 is `{chapter_prefix}02`, and later "
        "events keep the same zero-padded sequence.\n"
        f"If you introduce `F001` and the second timeline event is a major turning point, `coverage_markers` must "
        f"include both `F001` and `{chapter_prefix}02`."
    )


def _render_synopsis_coverage_requirements(synopsis_coverage: SynopsisCoveragePromptContext) -> str:
    lines = [
        "## synopsis_coverage_requirements",
        "List every pre-write required ID below inside `## coverage_markers` whenever you output `## synopsis_new`.",
        "Then add any new tracked foreshadowing IDs or current-chapter major turning point IDs created by this write.",
        "",
        "foreshadowing_ids:",
        *_render_id_list(synopsis_coverage.foreshadowing_ids),
        "major_turning_points:",
        *_render_id_list(synopsis_coverage.major_turning_points),
        "archived_major_turning_points:",
        *_render_id_list(synopsis_coverage.archived_major_turning_points),
    ]
    return "\n".join(lines)


def _render_id_list(ids: tuple[str, ...]) -> list[str]:
    if not ids:
        return ["- (none)"]
    return [f"- {item}" for item in ids]


def _ordered_unique(values) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)
