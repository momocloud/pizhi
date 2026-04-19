from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from pizhi.adapters.provider_base import ProviderResponse
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.checkpoint_store import CheckpointStore
from pizhi.services.continue_execution import resume_continue_execution
from pizhi.services.continue_execution import start_continue_execution
from pizhi.services.continue_session_store import ContinueSessionStore
from pizhi.services.outline_service import OutlineService
from pizhi.services.prompt_budget import PromptBudgetError


@dataclass
class StubAdapter:
    content_text: str

    def execute(self, request):
        return ProviderResponse(
            raw_payload={"id": "resp_test"},
            content_text=self.content_text,
        )


@dataclass
class FailingAdapter:
    error_message: str = "provider request failed"

    def execute(self, request):
        raise RuntimeError(self.error_message)


def _configure_provider(project_root) -> None:
    config = load_config(project_root / ".pizhi" / "config.yaml")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    save_config(project_root / ".pizhi" / "config.yaml", config)


def _seed_drafted_range(project_root, start: int, end: int) -> None:
    paths = project_paths(project_root)
    store = ChapterIndexStore(paths.chapter_index_file)
    for chapter_number in range(start, end + 1):
        store.upsert(
            {
                "n": chapter_number,
                "title": f"第{chapter_number:03d}章",
                "vol": 1,
                "status": "drafted",
                "summary": "",
                "updated": date.today().isoformat(),
            }
        )


def _outline_response(start: int, end: int) -> str:
    blocks: list[str] = []
    for chapter_number in range(start, end + 1):
        blocks.append(
            f"## ch{chapter_number:03d} | 第{chapter_number:03d}章\n"
            f"- beat for chapter {chapter_number}\n"
        )
    return "\n".join(blocks)


def _only_session(project_root):
    sessions_dir = project_paths(project_root).continue_sessions_dir
    session_ids = [entry.name for entry in sessions_dir.iterdir() if entry.is_dir()]
    assert len(session_ids) == 1
    return ContinueSessionStore(sessions_dir).load(session_ids[0])


def _only_checkpoint(project_root):
    checkpoints_dir = project_paths(project_root).checkpoints_dir
    checkpoint_ids = [entry.name for entry in checkpoints_dir.iterdir() if entry.is_dir()]
    assert len(checkpoint_ids) == 1
    return CheckpointStore(checkpoints_dir).load(checkpoint_ids[0])


def test_start_continue_execution_creates_waiting_outline_checkpoint(initialized_project, monkeypatch):
    _configure_provider(initialized_project)
    _seed_drafted_range(initialized_project, 1, 2)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StubAdapter(_outline_response(3, 5)),
    )

    result = start_continue_execution(initialized_project, count=4, direction="push the dock war")

    assert result.session.start_chapter == 3
    assert result.session.target_end_chapter == 6
    assert result.session.current_stage == "outline"
    assert result.session.current_range == (3, 5)
    assert result.session.status == "waiting_apply"
    assert result.checkpoint.stage == "outline"
    assert result.checkpoint.chapter_range == (3, 5)
    assert result.checkpoint.status == "generated"
    assert len(result.checkpoint.run_ids) == 1


def test_resume_continue_execution_rejects_session_that_is_not_ready(initialized_project):
    store = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir)
    session = store.create(
        count=3,
        direction="hold position",
        start_chapter=1,
        target_end_chapter=3,
        current_stage="outline",
        current_range=(1, 3),
        last_checkpoint_id="checkpoint-1",
        status="waiting_apply",
    )

    with pytest.raises(ValueError, match="not ready to resume"):
        resume_continue_execution(initialized_project, session.session_id)


def test_resume_continue_execution_moves_applied_outline_to_write_checkpoint(initialized_project, monkeypatch):
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    OutlineService(initialized_project).apply_response(_outline_response(1, 3))
    store = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir)
    session = store.create(
        count=3,
        direction="hold position",
        start_chapter=1,
        target_end_chapter=3,
        current_stage="outline",
        current_range=(1, 3),
        last_checkpoint_id="checkpoint-outline",
        status="ready_to_resume",
    )
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StubAdapter("# chapter draft"),
    )

    result = resume_continue_execution(initialized_project, session.session_id)

    assert result.session.current_stage == "write"
    assert result.session.current_range == (1, 3)
    assert result.session.status == "waiting_apply"
    assert result.checkpoint is not None
    assert result.checkpoint.stage == "write"
    assert result.checkpoint.chapter_range == (1, 3)
    assert result.checkpoint.status == "generated"
    assert len(result.checkpoint.run_ids) == 3


def test_resume_continue_execution_marks_session_completed_after_last_write(initialized_project):
    store = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir)
    session = store.create(
        count=3,
        direction="hold position",
        start_chapter=1,
        target_end_chapter=3,
        current_stage="write",
        current_range=(1, 3),
        last_checkpoint_id="checkpoint-write",
        status="ready_to_resume",
    )

    result = resume_continue_execution(initialized_project, session.session_id)

    assert result.checkpoint is None
    assert result.session.current_stage == "write"
    assert result.session.current_range == (1, 3)
    assert result.session.status == "completed"


@pytest.mark.parametrize(
    ("adapter", "message"),
    [
        (FailingAdapter(), "provider_failed"),
        (StubAdapter(""), "normalize_failed"),
    ],
)
def test_start_continue_execution_blocks_session_on_provider_failures(
    initialized_project, monkeypatch, adapter, message
):
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: adapter,
    )

    with pytest.raises(ValueError, match=message):
        start_continue_execution(initialized_project, count=3, direction="push the dock war")

    session = _only_session(initialized_project)
    checkpoint = _only_checkpoint(initialized_project)
    assert session.status == "blocked"
    assert session.last_checkpoint_id == checkpoint.checkpoint_id
    assert checkpoint.status == "failed"


def test_resume_continue_execution_blocks_session_on_write_budget_failure(initialized_project, monkeypatch):
    OutlineService(initialized_project).apply_response(_outline_response(1, 3))
    store = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir)
    session = store.create(
        count=3,
        direction="hold position",
        start_chapter=1,
        target_end_chapter=3,
        current_stage="outline",
        current_range=(1, 3),
        last_checkpoint_id="checkpoint-outline",
        status="ready_to_resume",
    )
    monkeypatch.setattr(
        "pizhi.services.continue_execution.ensure_write_prompt_within_budget",
        lambda **_: (_ for _ in ()).throw(PromptBudgetError("write prompt exceeds budget for ch001")),
    )

    with pytest.raises(ValueError, match="write prompt exceeds budget for ch001"):
        resume_continue_execution(initialized_project, session.session_id)

    checkpoint = _only_checkpoint(initialized_project)
    blocked = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir).load(session.session_id)
    assert blocked.status == "blocked"
    assert blocked.last_checkpoint_id == checkpoint.checkpoint_id
    assert checkpoint.stage == "write"
    assert checkpoint.status == "failed"
