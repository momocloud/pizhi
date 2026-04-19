from __future__ import annotations

import re
from dataclasses import dataclass

from pizhi.adapters.provider_base import ProviderResponse
from pizhi.cli import main
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.paths import project_paths
from pizhi.services.checkpoint_store import CheckpointStore
from pizhi.services.continue_session_store import ContinueSessionStore
from pizhi.services.prompt_budget import PromptBudgetError


CHAPTER_THREE_RESPONSE = """---
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
  referenced: []
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
"""


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


def _single_checkpoint(project_root):
    paths = project_paths(project_root)
    checkpoint_ids = [entry.name for entry in paths.checkpoints_dir.iterdir() if entry.is_dir()]
    assert len(checkpoint_ids) == 1
    return CheckpointStore(paths.checkpoints_dir).load(checkpoint_ids[0])


def _line_value(output: str, prefix: str) -> str:
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip().split()[0]
    raise AssertionError(f"missing line starting with {prefix!r}: {output}")


def _latest_checkpoint(project_root):
    paths = project_paths(project_root)
    checkpoint_ids = sorted(entry.name for entry in paths.checkpoints_dir.iterdir() if entry.is_dir())
    assert checkpoint_ids
    return CheckpointStore(paths.checkpoints_dir).load(checkpoint_ids[-1])


def test_continue_execute_creates_real_session_and_outline_checkpoint(initialized_project, monkeypatch):
    monkeypatch.chdir(initialized_project)
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RoutedAdapter(outline_text=_outline_response(1, 3), chapter_responses={}),
    )

    result = main(["continue", "--count", "3", "--execute"])

    assert result == 0
    session = _single_session(initialized_project)
    checkpoint = _single_checkpoint(initialized_project)
    paths = project_paths(initialized_project)
    assert session.manifest_path == paths.continue_sessions_dir / session.session_id / "manifest.json"
    assert session.manifest_path.exists()
    assert checkpoint.manifest_path == paths.checkpoints_dir / checkpoint.checkpoint_id / "manifest.json"
    assert checkpoint.manifest_path.exists()
    assert session.current_stage == "outline"
    assert session.status == "waiting_apply"
    assert session.last_checkpoint_id == checkpoint.checkpoint_id
    assert checkpoint.session_id == session.session_id
    assert checkpoint.stage == "outline"
    assert checkpoint.status == "generated"
    assert checkpoint.chapter_range == (1, 3)


def test_continue_resume_returns_error_and_blocks_session_when_write_prompt_exceeds_budget(
    initialized_project, monkeypatch, capsys
):
    monkeypatch.chdir(initialized_project)
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RoutedAdapter(outline_text=_outline_response(1, 3), chapter_responses={}),
    )

    execute_exit = main(["continue", "--count", "3", "--execute"])
    execute_output = capsys.readouterr().out
    session_id = _line_value(execute_output, "session_id=")
    checkpoint_id = _line_value(execute_output, "checkpoint_id=")

    assert execute_exit == 0
    assert checkpoint_id

    apply_exit = main(["checkpoint", "apply", "--id", checkpoint_id])
    assert apply_exit == 0

    monkeypatch.setattr(
        "pizhi.services.continue_execution.ensure_write_prompt_within_budget",
        lambda **_: (_ for _ in ()).throw(PromptBudgetError("write prompt exceeds budget for ch001")),
    )

    resume_exit = main(["continue", "resume", "--session-id", session_id])
    captured = capsys.readouterr()
    session = _single_session(initialized_project)
    checkpoint = _latest_checkpoint(initialized_project)

    assert resume_exit == 1
    assert "error:" in captured.err
    assert "write prompt exceeds budget for ch001" in captured.err
    assert session.status == "blocked"
    assert checkpoint.stage == "write"
    assert checkpoint.status == "failed"


def test_legacy_continue_prompt_only_flow_still_works(initialized_project, monkeypatch, fixture_text, capsys):
    monkeypatch.chdir(initialized_project)
    outline_response = initialized_project / "outline_expand_response.md"
    outline_response.write_text(
        fixture_text("outline_expand_response.md")
        + "\n## ch003 | 暗巷回声\n- 沈轩在暗巷被顾临截住。\n- 血衣线索首次闭环。\n",
        encoding="utf-8",
        newline="\n",
    )

    responses_dir = initialized_project / "chapter_responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    (responses_dir / "ch001_response.md").write_text(fixture_text("ch001_response.md"), encoding="utf-8", newline="\n")
    (responses_dir / "ch002_response.md").write_text(fixture_text("ch002_response.md"), encoding="utf-8", newline="\n")
    (responses_dir / "ch003_response.md").write_text(CHAPTER_THREE_RESPONSE, encoding="utf-8", newline="\n")

    result = main(
        [
            "continue",
            "--count",
            "3",
            "--outline-response-file",
            str(outline_response),
            "--chapter-responses-dir",
            str(responses_dir),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "Continued chapters ch001-ch003" in captured.out
    assert not project_paths(initialized_project).continue_sessions_dir.exists()
    assert not project_paths(initialized_project).checkpoints_dir.exists()
