from __future__ import annotations

import re
from dataclasses import dataclass

from pizhi.adapters.provider_base import ProviderResponse
from pizhi.cli import main
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.paths import project_paths
from pizhi.services.maintenance import MaintenanceFinding
from pizhi.services.maintenance import MaintenanceResult
from pizhi.services.checkpoint_store import CheckpointStore
from pizhi.services.continue_session_store import ContinueSessionStore
from pizhi.services.write_candidate_validation import validate_write_candidate


CHAPTER_RESPONSES = {
    1: """---
chapter_title: "第一章 雨夜访客"
word_count_estimated: 2800
characters_involved:
  - 沈轩
worldview_changed: false
synopsis_changed: false
timeline_events:
  - at: "1986-03-14 夜"
    event: "沈轩目击命案"
    is_flashback: false
    is_major_turning_point: true
foreshadowing:
  introduced:
    - id: F001
      desc: "雨夜命案背后的见证者"
      planned_payoff: "ch003"
      priority: high
      related_characters:
        - 沈轩
  referenced: []
  resolved: []
---

沈轩在雨夜目击了第一起命案。

---

## characters_snapshot

# 第一章角色状态

## 沈轩
- **位置**：香港，旧港街头
- **状态**：惊惧，但决定追查

## relationships_snapshot

# 第一章人物关系

## 当前关系状态

| 从 | 到 | 关系 | 信任度 | 备注 |
|----|----|------|--------|------|
| 沈轩 | 顾临 | 试探 | 低 | 尚未建立信任 |

## 本章变化

| 关系 | 变化前 | 变化后 | 触发原因 |
|------|--------|--------|---------|
| 沈轩 → 顾临 | 陌生 | 试探 | 沈轩记住了顾临的名字 |
""",
    2: """---
chapter_title: "第二章 码头血衣"
word_count_estimated: 2900
characters_involved:
  - 沈轩
  - 顾临
worldview_changed: false
synopsis_changed: false
timeline_events:
  - at: "1986-03-15 凌晨"
    event: "顾临发现血衣"
    is_flashback: false
    is_major_turning_point: false
foreshadowing:
  introduced: []
  referenced:
    - id: F001
  resolved: []
---

顾临在码头仓库找到沾血的外套。

---

## characters_snapshot

# 第二章角色状态

## 沈轩
- **位置**：香港，旧港仓库外
- **状态**：继续掩饰线索来源

## 顾临
- **位置**：香港，旧港仓库
- **状态**：怀疑沈轩有所隐瞒

## relationships_snapshot

# 第二章人物关系

## 当前关系状态

| 从 | 到 | 关系 | 信任度 | 备注 |
|----|----|------|--------|------|
| 沈轩 | 顾临 | 试探 | 低 | 双方都未说真话 |

## 本章变化

| 关系 | 变化前 | 变化后 | 触发原因 |
|------|--------|--------|---------|
| 沈轩 → 顾临 | 试探 | 对抗 | 血衣线索引发冲突 |
""",
    3: """---
chapter_title: "第三章 暗巷回声"
word_count_estimated: 3100
characters_involved:
  - 沈轩
  - 顾临
worldview_changed: false
synopsis_changed: false
timeline_events:
  - at: "1986-03-15 夜"
    event: "沈轩在暗巷与顾临短暂交锋"
    is_flashback: false
    is_major_turning_point: true
foreshadowing:
  introduced: []
  referenced:
    - id: F001
  resolved:
    - id: F001
---

顾临终于在暗巷拦住了沈轩，问他血衣究竟从哪里来。

---

## characters_snapshot

# 第三章角色状态

## 沈轩
- **位置**：香港，旧城暗巷
- **状态**：试图隐瞒血衣来源，但已经动摇

## 顾临
- **位置**：香港，旧城暗巷
- **状态**：怀疑加深，决定独自追查

## relationships_snapshot

# 第三章人物关系

## 当前关系状态

| 从 | 到 | 关系 | 信任度 | 备注 |
|----|----|------|--------|------|
| 沈轩 | 顾临 | 对抗 + 利用 | 低 | 各自隐瞒关键信息 |

## 本章变化

| 关系 | 变化前 | 变化后 | 触发原因 |
|------|--------|--------|---------|
| 沈轩 → 顾临 | 试探 | 对抗 + 利用 | 顾临逼问血衣来源 |
""",
}


def test_checkpoint_write_response_fixtures_follow_current_write_contract():
    for chapter_number, response in sorted(CHAPTER_RESPONSES.items()):
        validate_write_candidate(response)


@dataclass
class RoutedAdapter:
    outline_text: str
    chapter_responses: dict[int, str]

    def execute(self, request):
        if request.prompt_text.startswith("# Outline Expansion Request"):
            content_text = self.outline_text
        else:
            match = re.search(r"^Chapter: (?P<chapter>\d+)$", request.prompt_text, re.MULTILINE)
            assert match is not None
            content_text = self.chapter_responses[int(match.group("chapter"))]
        return ProviderResponse(
            raw_payload={"id": "resp_test"},
            content_text=content_text,
        )


def _configure_provider(project_root) -> None:
    config = load_config(project_root / ".pizhi" / "config.yaml")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    save_config(project_root / ".pizhi" / "config.yaml", config)


def _outline_response(start: int, end: int) -> str:
    return "\n".join(
        [
            f"## ch{chapter_number:03d} | 第{chapter_number:03d}章\n"
            f"- beat for chapter {chapter_number}\n"
            for chapter_number in range(start, end + 1)
        ]
    )


def _single_session(project_root):
    paths = project_paths(project_root)
    session_ids = [entry.name for entry in paths.continue_sessions_dir.iterdir() if entry.is_dir()]
    assert len(session_ids) == 1
    return ContinueSessionStore(paths.continue_sessions_dir).load(session_ids[0])


def _all_checkpoints(project_root):
    paths = project_paths(project_root)
    store = CheckpointStore(paths.checkpoints_dir)
    return [store.load(entry.name) for entry in sorted(paths.checkpoints_dir.iterdir()) if entry.is_dir()]


def _start_execute_session(project_root, monkeypatch):
    monkeypatch.chdir(project_root)
    _configure_provider(project_root)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RoutedAdapter(outline_text=_outline_response(1, 3), chapter_responses=CHAPTER_RESPONSES),
    )
    assert main(["continue", "--count", "3", "--execute"]) == 0


def test_checkpoint_apply_then_continue_resume_advances_to_write(initialized_project, monkeypatch):
    _start_execute_session(initialized_project, monkeypatch)
    session = _single_session(initialized_project)
    outline_checkpoint = _all_checkpoints(initialized_project)[0]

    assert main(["checkpoint", "apply", "--id", outline_checkpoint.checkpoint_id]) == 0

    applied_checkpoint = CheckpointStore(project_paths(initialized_project).checkpoints_dir).load(
        outline_checkpoint.checkpoint_id
    )
    ready_session = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir).load(
        session.session_id
    )
    assert applied_checkpoint.stage == "outline"
    assert applied_checkpoint.status == "applied"
    assert ready_session.status == "ready_to_resume"

    assert main(["continue", "resume", "--session-id", session.session_id]) == 0

    resumed_session = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir).load(
        session.session_id
    )
    checkpoints = _all_checkpoints(initialized_project)
    write_checkpoint = next(checkpoint for checkpoint in checkpoints if checkpoint.stage == "write")
    assert resumed_session.current_stage == "write"
    assert resumed_session.status == "waiting_apply"
    assert resumed_session.last_checkpoint_id == write_checkpoint.checkpoint_id
    assert write_checkpoint.status == "generated"
    assert write_checkpoint.chapter_range == (1, 3)


def test_continue_sessions_and_checkpoints_list_real_fields(initialized_project, monkeypatch, capsys):
    _start_execute_session(initialized_project, monkeypatch)
    session = _single_session(initialized_project)
    checkpoint = _all_checkpoints(initialized_project)[0]
    capsys.readouterr()

    assert main(["continue", "sessions"]) == 0

    sessions_output = capsys.readouterr()
    assert f"session_id={session.session_id}" in sessions_output.out
    assert f"checkpoint_id={checkpoint.checkpoint_id}" in sessions_output.out
    assert "stage=outline" in sessions_output.out
    assert "status=waiting_apply" in sessions_output.out

    assert main(["checkpoints", "--session-id", session.session_id]) == 0

    checkpoints_output = capsys.readouterr()
    assert f"checkpoint_id={checkpoint.checkpoint_id}" in checkpoints_output.out
    assert f"session_id={session.session_id}" in checkpoints_output.out
    assert "stage=outline" in checkpoints_output.out
    assert "status=generated" in checkpoints_output.out


def test_checkpoint_apply_fails_preflight_when_session_manifest_is_missing(
    initialized_project, monkeypatch, capsys
):
    _start_execute_session(initialized_project, monkeypatch)
    session = _single_session(initialized_project)
    checkpoint = _all_checkpoints(initialized_project)[0]
    session.manifest_path.unlink()
    capsys.readouterr()

    result = main(["checkpoint", "apply", "--id", checkpoint.checkpoint_id])

    captured = capsys.readouterr()
    reloaded_checkpoint = CheckpointStore(project_paths(initialized_project).checkpoints_dir).load(
        checkpoint.checkpoint_id
    )
    assert result != 0
    assert "error:" in captured.err
    assert reloaded_checkpoint.status != "applied"


def test_checkpoint_apply_prints_each_write_run_maintenance_summary(initialized_project, monkeypatch, capsys):
    @dataclass(frozen=True, slots=True)
    class StubCheckpoint:
        checkpoint_id: str = "checkpoint-123"
        session_id: str = "session-456"
        stage: str = "write"
        status: str = "applied"

    @dataclass(frozen=True, slots=True)
    class StubSession:
        session_id: str = "session-456"
        last_checkpoint_id: str = "checkpoint-123"
        current_stage: str = "write"
        status: str = "ready_to_resume"

    @dataclass(frozen=True, slots=True)
    class StubCheckpointApplyResult:
        checkpoint: StubCheckpoint
        session: StubSession
        maintenance_results: list[tuple[int, MaintenanceResult | None]]

    maintenance_result = MaintenanceResult(
        synopsis_review=None,
        archive_result=None,
        findings=[MaintenanceFinding(category="Maintenance agent", detail="archive.audit: failed - boom")],
    )

    monkeypatch.setattr("pizhi.commands.checkpoint_cmd._preflight_checkpoint_apply", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "pizhi.commands.checkpoint_cmd.apply_checkpoint",
        lambda *_args, **_kwargs: StubCheckpointApplyResult(
            checkpoint=StubCheckpoint(),
            session=StubSession(),
            maintenance_results=[(1, maintenance_result)],
        ),
    )

    result = main(["checkpoint", "apply", "--id", "checkpoint-123"])

    captured = capsys.readouterr()
    assert result == 0
    assert "checkpoint_id=checkpoint-123" in captured.out
    assert "session_id=session-456" in captured.out
    assert "Maintenance agent: archive.audit: failed - boom" in captured.out


def test_continue_resume_fails_cleanly_when_session_manifest_is_missing(
    initialized_project, monkeypatch, capsys
):
    _start_execute_session(initialized_project, monkeypatch)
    session = _single_session(initialized_project)
    session.manifest_path.unlink()
    capsys.readouterr()

    result = main(["continue", "resume", "--session-id", session.session_id])

    captured = capsys.readouterr()
    assert result != 0
    assert "error:" in captured.err
    assert "Traceback" not in captured.err
