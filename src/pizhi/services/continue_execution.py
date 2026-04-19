from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.checkpoint_store import CheckpointRecord
from pizhi.services.checkpoint_store import CheckpointStore
from pizhi.services.continue_service import ContinueService
from pizhi.services.continue_service import validate_positive_int
from pizhi.services.continue_session_store import ContinueSessionRecord
from pizhi.services.continue_session_store import ContinueSessionStore
from pizhi.services.outline_service import OutlineService
from pizhi.services.prompt_budget import OutlineBatchPlanner
from pizhi.services.prompt_budget import PromptBudgetError
from pizhi.services.prompt_budget import ensure_write_prompt_within_budget
from pizhi.services.provider_execution import execute_prompt_request
from pizhi.services.write_service import WriteService

DEFAULT_OUTLINE_MAX_PROMPT_CHARS = 12_000
DEFAULT_WRITE_MAX_PROMPT_CHARS = 20_000


@dataclass(frozen=True, slots=True)
class ContinueExecutionResult:
    session: ContinueSessionRecord
    checkpoint: CheckpointRecord | None


def start_continue_execution(project_root: Path, *, count: int, direction: str = "") -> ContinueExecutionResult:
    continue_service = ContinueService(project_root)
    chapter_range = continue_service.determine_chapter_range(count)
    current_range = _first_checkpoint_range(project_root, chapter_range)
    session_store = ContinueSessionStore(project_paths(project_root).continue_sessions_dir)
    session = session_store.create(
        count=count,
        direction=direction,
        start_chapter=chapter_range[0],
        target_end_chapter=chapter_range[1],
        current_stage="outline",
        current_range=current_range,
        last_checkpoint_id=None,
        status="running",
    )
    return _generate_outline_result(project_root, session)


def resume_continue_execution(project_root: Path, session_id: str) -> ContinueExecutionResult:
    session_store = ContinueSessionStore(project_paths(project_root).continue_sessions_dir)
    session = session_store.load(session_id)
    if session.status != "ready_to_resume":
        raise ValueError(f"session {session_id} is not ready to resume")

    if session.current_stage == "outline":
        session = session_store.update(session_id, current_stage="write", status="running")
        return _generate_write_result(project_root, session)

    if session.current_stage == "write":
        next_range = _next_checkpoint_range(project_root, session)
        if next_range is None:
            completed = session_store.update(session_id, status="completed")
            return ContinueExecutionResult(session=completed, checkpoint=None)
        session = session_store.update(session_id, current_stage="outline", current_range=next_range, status="running")
        return _generate_outline_result(project_root, session)

    raise ValueError(f"session {session_id} has unsupported stage {session.current_stage}")


def _generate_outline_result(project_root: Path, session: ContinueSessionRecord) -> ContinueExecutionResult:
    outline_service = OutlineService(project_root)
    chapter_numbers = list(range(session.current_range[0], session.current_range[1] + 1))
    planner = OutlineBatchPlanner(max_prompt_chars=DEFAULT_OUTLINE_MAX_PROMPT_CHARS)

    try:
        batch_ranges = planner.plan(
            chapter_numbers,
            lambda chapter_number: outline_service.build_prompt_request(
                (chapter_number, chapter_number),
                direction=session.direction,
            ).prompt_text,
        )
    except PromptBudgetError as exc:
        return _raise_failed_checkpoint(project_root, session, stage="outline", run_ids=[], error_message=str(exc))

    run_ids: list[str] = []
    for batch_range in batch_ranges:
        request = outline_service.build_prompt_request(batch_range, direction=session.direction)
        target = _format_range_target(batch_range)
        try:
            execution = execute_prompt_request(
                project_root,
                request,
                target=target,
            )
        except ValueError as exc:
            return _raise_failed_checkpoint(
                project_root,
                session,
                stage="outline",
                run_ids=run_ids,
                error_message=str(exc),
            )
        run_ids.append(execution.run_id)
        if execution.status != "succeeded":
            message = (
                f"outline checkpoint generation failed for {target}: {execution.status}"
            )
            return _raise_failed_checkpoint(
                project_root,
                session,
                stage="outline",
                run_ids=run_ids,
                error_message=message,
            )

    checkpoint = CheckpointStore(project_paths(project_root).checkpoints_dir).create(
        session_id=session.session_id,
        stage="outline",
        chapter_range=session.current_range,
        run_ids=run_ids,
        status="generated",
    )
    updated_session = ContinueSessionStore(project_paths(project_root).continue_sessions_dir).update(
        session.session_id,
        last_checkpoint_id=checkpoint.checkpoint_id,
        status="waiting_apply",
    )
    return ContinueExecutionResult(session=updated_session, checkpoint=checkpoint)


def _generate_write_result(project_root: Path, session: ContinueSessionRecord) -> ContinueExecutionResult:
    write_service = WriteService(project_root)
    run_ids: list[str] = []

    for chapter_number in range(session.current_range[0], session.current_range[1] + 1):
        request = write_service.build_prompt_request(chapter_number)
        try:
            ensure_write_prompt_within_budget(
                chapter_number=chapter_number,
                prompt_text=request.prompt_text,
                max_prompt_chars=DEFAULT_WRITE_MAX_PROMPT_CHARS,
            )
        except PromptBudgetError as exc:
            return _raise_failed_checkpoint(
                project_root,
                session,
                stage="write",
                run_ids=run_ids,
                error_message=str(exc),
            )

        target = f"ch{chapter_number:03d}"
        try:
            execution = execute_prompt_request(
                project_root,
                request,
                target=target,
            )
        except ValueError as exc:
            return _raise_failed_checkpoint(
                project_root,
                session,
                stage="write",
                run_ids=run_ids,
                error_message=str(exc),
            )
        run_ids.append(execution.run_id)
        if execution.status != "succeeded":
            message = f"write checkpoint generation failed for {target}: {execution.status}"
            return _raise_failed_checkpoint(
                project_root,
                session,
                stage="write",
                run_ids=run_ids,
                error_message=message,
            )

    checkpoint = CheckpointStore(project_paths(project_root).checkpoints_dir).create(
        session_id=session.session_id,
        stage="write",
        chapter_range=session.current_range,
        run_ids=run_ids,
        status="generated",
    )
    updated_session = ContinueSessionStore(project_paths(project_root).continue_sessions_dir).update(
        session.session_id,
        last_checkpoint_id=checkpoint.checkpoint_id,
        status="waiting_apply",
    )
    return ContinueExecutionResult(session=updated_session, checkpoint=checkpoint)


def _raise_failed_checkpoint(
    project_root: Path,
    session: ContinueSessionRecord,
    *,
    stage: str,
    run_ids: list[str],
    error_message: str,
) -> ContinueExecutionResult:
    checkpoint_store = CheckpointStore(project_paths(project_root).checkpoints_dir)
    checkpoint = checkpoint_store.create(
        session_id=session.session_id,
        stage=stage,
        chapter_range=session.current_range,
        run_ids=run_ids,
        status="failed",
    )
    ContinueSessionStore(project_paths(project_root).continue_sessions_dir).update(
        session.session_id,
        last_checkpoint_id=checkpoint.checkpoint_id,
        status="blocked",
    )
    raise ValueError(error_message)


def _first_checkpoint_range(project_root: Path, chapter_range: tuple[int, int]) -> tuple[int, int]:
    batch_size = _checkpoint_batch_size(project_root)
    start, end = chapter_range
    return (start, min(start + batch_size - 1, end))


def _next_checkpoint_range(project_root: Path, session: ContinueSessionRecord) -> tuple[int, int] | None:
    next_start = session.current_range[1] + 1
    if next_start > session.target_end_chapter:
        return None
    batch_size = _checkpoint_batch_size(project_root)
    return (next_start, min(next_start + batch_size - 1, session.target_end_chapter))


def _checkpoint_batch_size(project_root: Path) -> int:
    return validate_positive_int(
        ContinueService(project_root).config.consistency.checkpoint_interval,
        field_name="checkpoint_interval",
    )


def _format_range_target(chapter_range: tuple[int, int]) -> str:
    start, end = chapter_range
    if start == end:
        return f"ch{start:03d}"
    return f"ch{start:03d}-ch{end:03d}"
