from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from pizhi.adapters.base import PromptRequest
from pizhi.backends.base import ExecutionRequest
from pizhi.backends.opencode_backend import OpencodeExecutionBackend
from pizhi.core.config import AgentBackendSection
from pizhi.services.run_store import RunStore


def _backend_config() -> AgentBackendSection:
    return AgentBackendSection(
        agent_backend="opencode",
        agent_command="opencode",
        agent_args=["run"],
    )


def _execution_request(project_root: Path) -> ExecutionRequest:
    return ExecutionRequest(
        project_root=project_root,
        prompt_request=PromptRequest(
            command_name="write",
            prompt_text="# Write Request\n\nDraft the next chapter.\n",
            metadata={"chapter": 7},
            referenced_files=[".pizhi/chapters/ch007/outline.md"],
        ),
        target="ch007",
        route_name="write",
    )


def test_opencode_backend_reads_candidate_from_agent_output_file(tmp_path, monkeypatch):
    backend = OpencodeExecutionBackend()
    request = _execution_request(tmp_path)

    def fake_run(command, *, cwd, capture_output, text, encoding):
        assert command[:2] == ["opencode", "run"]
        assert "--agent" in command
        assert "--file" in command
        assert capture_output is True
        assert text is True
        Path(cwd, "agent_output.md").write_text(
            """---
chapter_title: 第七章
word_count_estimated: 1200
characters_involved: []
worldview_changed: false
synopsis_changed: false
timeline_events: []
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---
# 第七章

## characters_snapshot

- 沈轩

## relationships_snapshot

- 沈轩 -> 青石镇
""",
            encoding="utf-8",
        )
        return CompletedProcess(command, 0, stdout='{"event":"done"}\n', stderr="")

    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_run)

    result = backend.execute(request, backend_config=_backend_config())
    record = RunStore(tmp_path / ".pizhi" / "cache" / "runs").load(result.run_id)

    assert result.status == "succeeded"
    assert record.metadata["backend"] == "agent"
    assert record.metadata["agent_backend"] == "opencode"
    assert record.run_dir.joinpath("agent_task.md").exists()
    assert record.run_dir.joinpath("agent_request.json").exists()
    assert record.run_dir.joinpath("agent_output.md").exists()
    assert record.run_dir.joinpath("agent_stdout.txt").read_text(encoding="utf-8") == '{"event":"done"}\n'


def test_opencode_backend_treats_missing_output_file_as_failure(tmp_path, monkeypatch):
    backend = OpencodeExecutionBackend()
    request = _execution_request(tmp_path)

    def fake_run(command, *, cwd, capture_output, text, encoding):
        return CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_run)

    result = backend.execute(request, backend_config=_backend_config())
    record = RunStore(tmp_path / ".pizhi" / "cache" / "runs").load(result.run_id)

    assert result.status == "normalize_failed"
    assert "agent output file was not produced" in record.error_path.read_text(encoding="utf-8")


def test_opencode_backend_rejects_invalid_write_candidate_before_success(tmp_path, monkeypatch):
    backend = OpencodeExecutionBackend()
    request = _execution_request(tmp_path)

    def fake_run(command, *, cwd, capture_output, text, encoding):
        Path(cwd, "agent_output.md").write_text(
            """---
chapter_title: 第七章
word_count_estimated: 1200
characters_involved: []
worldview_changed: false
synopsis_changed: false
timeline_events: []
foreshadowing:
  introduced:
    - id: F001
      desc: "七日后，青石镇灭"的血字预言
      planned_payoff: 伏笔
      priority: high
      related_characters: []
  referenced: []
  resolved: []
---
正文
""",
            encoding="utf-8",
        )
        return CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_run)

    result = backend.execute(request, backend_config=_backend_config())
    record = RunStore(tmp_path / ".pizhi" / "cache" / "runs").load(result.run_id)

    assert result.status == "normalize_failed"
    assert record.status == "normalize_failed"
    assert "write candidate failed validation" in record.error_path.read_text(encoding="utf-8")


def test_opencode_backend_rejects_parseable_but_invalid_write_candidate_before_success(
    tmp_path, monkeypatch
):
    backend = OpencodeExecutionBackend()
    request = _execution_request(tmp_path)

    def fake_run(command, *, cwd, capture_output, text, encoding):
        Path(cwd, "agent_output.md").write_text(
            """---
chapter_title: 第七章
word_count_estimated: 1200
characters_involved: []
worldview_changed: false
synopsis_changed: false
timeline_events:
  - event: 没有时间字段的事件
    is_flashback: false
    is_major_turning_point: false
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---
正文

---

## characters_snapshot

- 沈轩

## relationships_snapshot

- 沈轩 -> 青石镇
""",
            encoding="utf-8",
        )
        return CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_run)

    result = backend.execute(request, backend_config=_backend_config())
    record = RunStore(tmp_path / ".pizhi" / "cache" / "runs").load(result.run_id)

    assert result.status == "normalize_failed"
    assert record.status == "normalize_failed"
    assert "write candidate failed validation" in record.error_path.read_text(encoding="utf-8")


def test_opencode_backend_repairs_invalid_write_candidate_once_before_success(tmp_path, monkeypatch):
    backend = OpencodeExecutionBackend()
    request = _execution_request(tmp_path)
    calls: list[list[str]] = []

    invalid_output = """---
chapter_title: 第七章
word_count_estimated: 1200
characters_involved:
  沈轩
  - 青石
worldview_changed: false
synopsis_changed: false
timeline_events: []
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---
正文

---

## characters_snapshot

- 沈轩

## relationships_snapshot

- 沈轩 -> 青石镇
"""
    repaired_output = """---
chapter_title: 第七章
word_count_estimated: 1200
characters_involved:
  - 沈轩
  - 青石
worldview_changed: false
synopsis_changed: false
timeline_events: []
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---
正文

---

## characters_snapshot

- 沈轩

## relationships_snapshot

- 沈轩 -> 青石镇
"""

    def fake_run(command, *, cwd, capture_output, text, encoding):
        calls.append(command)
        if len(calls) == 1:
            Path(cwd, "agent_output.md").write_text(invalid_output, encoding="utf-8")
        else:
            Path(cwd, "repair_output.md").write_text(repaired_output, encoding="utf-8")
        return CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_run)

    result = backend.execute(request, backend_config=_backend_config())
    record = RunStore(tmp_path / ".pizhi" / "cache" / "runs").load(result.run_id)

    assert result.status == "succeeded"
    assert len(calls) == 2
    assert record.run_dir.joinpath("repair_task.md").exists()
    assert record.run_dir.joinpath("repair_output.md").exists()


def test_opencode_backend_repair_task_explains_changed_flags_need_markdown_sections(tmp_path, monkeypatch):
    backend = OpencodeExecutionBackend()
    request = _execution_request(tmp_path)
    calls: list[list[str]] = []

    invalid_output = """---
chapter_title: 第七章
word_count_estimated: 1200
characters_involved:
  - 沈轩
worldview_changed: true
synopsis_changed: true
timeline_events: []
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---
正文

---

## characters_snapshot

- 沈轩

## relationships_snapshot

- 沈轩 -> 青石镇
"""
    repaired_output = """---
chapter_title: 第七章
word_count_estimated: 1200
characters_involved:
  - 沈轩
worldview_changed: true
synopsis_changed: true
timeline_events: []
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---
正文

---

## characters_snapshot

- 沈轩

## relationships_snapshot

- 沈轩 -> 青石镇

## worldview_patch

- 新增世界观规则。

## synopsis_new

# Synopsis

沈轩发现青石镇隐藏着新的规则。
"""

    def fake_run(command, *, cwd, capture_output, text, encoding):
        calls.append(command)
        if len(calls) == 1:
            Path(cwd, "agent_output.md").write_text(invalid_output, encoding="utf-8")
        else:
            repair_task = Path(cwd, "repair_task.md").read_text(encoding="utf-8")
            assert "Do not put `worldview_patch` or `synopsis_new` in YAML frontmatter." in repair_task
            assert "When `worldview_changed: true`, add a Markdown section named `## worldview_patch`" in repair_task
            assert "When `synopsis_changed: true`, add a Markdown section named `## synopsis_new`" in repair_task
            Path(cwd, "repair_output.md").write_text(repaired_output, encoding="utf-8")
        return CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_run)

    result = backend.execute(request, backend_config=_backend_config())
    record = RunStore(tmp_path / ".pizhi" / "cache" / "runs").load(result.run_id)

    assert result.status == "succeeded"
    assert len(calls) == 2
    assert record.run_dir.joinpath("repair_task.md").exists()


def test_opencode_backend_keeps_normalize_failed_when_repair_output_is_still_invalid(tmp_path, monkeypatch):
    backend = OpencodeExecutionBackend()
    request = _execution_request(tmp_path)
    calls: list[list[str]] = []

    invalid_output = """---
chapter_title: 第七章
word_count_estimated: 1200
characters_involved:
  沈轩
  - 青石
worldview_changed: false
synopsis_changed: false
timeline_events: []
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---
正文

---

## characters_snapshot

- 沈轩

## relationships_snapshot

- 沈轩 -> 青石镇
"""

    def fake_run(command, *, cwd, capture_output, text, encoding):
        calls.append(command)
        if len(calls) == 1:
            Path(cwd, "agent_output.md").write_text(invalid_output, encoding="utf-8")
        else:
            Path(cwd, "repair_output.md").write_text(invalid_output, encoding="utf-8")
        return CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_run)

    result = backend.execute(request, backend_config=_backend_config())
    record = RunStore(tmp_path / ".pizhi" / "cache" / "runs").load(result.run_id)

    assert result.status == "normalize_failed"
    assert len(calls) == 2
    assert record.run_dir.joinpath("repair_task.md").exists()
    assert record.run_dir.joinpath("repair_output.md").exists()
    assert "write candidate failed validation" in record.error_path.read_text(encoding="utf-8")


def test_opencode_backend_rejects_non_opencode_backend_override(tmp_path):
    backend = OpencodeExecutionBackend()
    request = _execution_request(tmp_path)

    with pytest.raises(ValueError, match="unsupported agent backend"):
        backend.execute(
            request,
            backend_config=AgentBackendSection(
                agent_backend="other",
                agent_command="other",
                agent_args=[],
            ),
        )
