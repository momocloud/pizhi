from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
import pytest

from pizhi.cli import main
from pizhi.core.config import AgentBackendSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config

from tests.unit.test_provider_execution import FailingAdapter
from tests.unit.test_provider_execution import StubAdapter
from tests.unit.test_provider_execution import _configure_provider
from pizhi.services.run_store import RunStore


def _configure_agent_backend(project_root) -> None:
    config = load_config(project_root / ".pizhi" / "config.yaml")
    config.execution.backend = "agent"
    config.execution.agent = AgentBackendSection(
        agent_backend="opencode",
        agent_command="opencode",
        agent_args=["run"],
    )
    save_config(project_root / ".pizhi" / "config.yaml", config)


@pytest.mark.parametrize(
    ("argv", "response_file_name"),
    [
        (["brainstorm", "--execute"], "brainstorm_response.md"),
        (["outline", "expand", "--chapters", "1-2", "--execute"], "outline_response.md"),
        (["write", "--chapter", "1", "--execute"], "write_response.md"),
    ],
)
def test_execute_rejects_response_file_conflict(initialized_project, monkeypatch, capsys, argv, response_file_name):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    _configure_provider(initialized_project)
    response_file = initialized_project / response_file_name
    response_file.write_text("raw response", encoding="utf-8")

    exit_code = main([*argv, "--response-file", str(response_file)])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "--execute cannot be used with --response-file" in captured.err


@pytest.mark.parametrize(
    ("argv", "expected_error"),
    [
        (["brainstorm", "--execute"], "provider is not configured"),
        (["outline", "expand", "--chapters", "1-2", "--execute"], "provider is not configured"),
        (["write", "--chapter", "1", "--execute"], "provider is not configured"),
    ],
)
def test_execute_reports_missing_provider_config_without_traceback(
    initialized_project,
    monkeypatch,
    capsys,
    argv,
    expected_error,
):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    exit_code = main(argv)
    captured = capsys.readouterr()

    assert exit_code != 0
    assert expected_error in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    ("argv", "setup"),
    [
        (["brainstorm", "--execute"], "brainstorm"),
        (["outline", "expand", "--chapters", "1-2", "--execute"], "outline"),
        (["write", "--chapter", "1", "--execute"], "write"),
    ],
)
def test_execute_reports_missing_api_key_without_traceback(
    initialized_project,
    monkeypatch,
    capsys,
    argv,
    setup,
):
    monkeypatch.chdir(initialized_project)
    _configure_provider(initialized_project)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    if setup == "write":
        chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        (chapter_dir / "outline.md").write_text(
            "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
            encoding="utf-8",
        )

    exit_code = main(argv)
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "OPENAI_API_KEY is not set" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    ("argv", "setup"),
    [
        (["brainstorm", "--execute"], "brainstorm"),
        (["outline", "expand", "--chapters", "1-2", "--execute"], "outline"),
        (["write", "--chapter", "1", "--execute"], "write"),
    ],
)
def test_execute_reports_provider_failure_without_traceback(
    initialized_project,
    monkeypatch,
    capsys,
    argv,
    setup,
):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    _configure_provider(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: FailingAdapter("provider request failed"),
    )

    if setup == "write":
        chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        (chapter_dir / "outline.md").write_text(
            "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
            encoding="utf-8",
        )

    exit_code = main(argv)
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "provider request failed" in captured.err
    assert "Traceback" not in captured.err
    assert "Run ID:" in captured.out


@pytest.mark.parametrize(
    ("argv", "setup"),
    [
        (["brainstorm", "--execute"], "brainstorm"),
        (["outline", "expand", "--chapters", "1-2", "--execute"], "outline"),
        (["write", "--chapter", "1", "--execute"], "write"),
    ],
)
def test_execute_reports_normalize_failure_without_traceback(
    initialized_project,
    monkeypatch,
    capsys,
    argv,
    setup,
):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    _configure_provider(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StubAdapter(""),
    )

    if setup == "write":
        chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        (chapter_dir / "outline.md").write_text(
            "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
            encoding="utf-8",
        )

    exit_code = main(argv)
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "provider response did not contain text content" in captured.err
    assert "Traceback" not in captured.err
    assert "Run ID:" in captured.out


def test_brainstorm_execute_writes_run_id_and_run_artifacts(initialized_project, monkeypatch, capsys):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    _configure_provider(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StubAdapter("## synopsis\n..."),
    )

    exit_code = main(["brainstorm", "--execute"])
    captured = capsys.readouterr()

    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"
    run_id = _extract_run_id(captured.out)
    record = RunStore(runs_dir).load(run_id)

    assert exit_code == 0
    assert "Prepared prompt packet:" in captured.out
    assert "Run ID:" in captured.out
    assert any(path.joinpath("normalized.md").exists() for path in runs_dir.iterdir())
    assert record.metadata["model"] == "gpt-5.4-brainstorm"


def test_outline_execute_writes_run_id_and_run_artifacts(initialized_project, monkeypatch, capsys):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    _configure_provider(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StubAdapter("## outline\n..."),
    )

    exit_code = main(["outline", "expand", "--chapters", "1-2", "--execute"])
    captured = capsys.readouterr()

    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"
    run_id = _extract_run_id(captured.out)
    record = RunStore(runs_dir).load(run_id)

    assert exit_code == 0
    assert "Prepared prompt packet:" in captured.out
    assert "Run ID:" in captured.out
    assert any(path.joinpath("normalized.md").exists() for path in runs_dir.iterdir())
    assert record.metadata["model"] == "gpt-5.4-outline"


def test_write_execute_writes_run_id_and_run_artifacts(initialized_project, monkeypatch, capsys):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    _configure_provider(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StubAdapter(
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
"""
        ),
    )

    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
        encoding="utf-8",
    )

    exit_code = main(["write", "--chapter", "1", "--execute"])
    captured = capsys.readouterr()

    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"
    run_id = _extract_run_id(captured.out)
    record = RunStore(runs_dir).load(run_id)

    assert exit_code == 0
    assert "Prepared prompt packet:" in captured.out
    assert "Run ID:" in captured.out
    assert any(path.joinpath("normalized.md").exists() for path in runs_dir.iterdir())
    assert record.metadata["model"] == "gpt-5.4-write"


def test_write_execute_keeps_prompt_only_flow_when_execute_is_omitted(initialized_project, monkeypatch):
    monkeypatch.chdir(initialized_project)
    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
        encoding="utf-8",
    )

    exit_code = main(["write", "--chapter", "1"])

    assert exit_code == 0
    assert (initialized_project / ".pizhi" / "cache" / "prompts").exists()


@pytest.mark.parametrize(
    "argv",
    [
        ["brainstorm"],
        ["outline", "expand", "--chapters", "1-2"],
    ],
)
def test_execute_commands_keep_prompt_only_flow_when_execute_is_omitted(initialized_project, monkeypatch, argv):
    monkeypatch.chdir(initialized_project)

    exit_code = main(argv)

    assert exit_code == 0
    assert (initialized_project / ".pizhi" / "cache" / "prompts").exists()


@pytest.mark.parametrize(
    ("argv", "setup", "expected_command", "output_text"),
    [
        (["brainstorm", "--execute"], "none", "brainstorm", "## synopsis\n...\n"),
        (["outline", "expand", "--chapters", "1-2", "--execute"], "none", "outline-expand", "## outline\n...\n"),
        (
            ["write", "--chapter", "1", "--execute"],
            "write",
            "write",
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
        ),
    ],
)
def test_execute_commands_write_agent_backend_run_artifacts(
    initialized_project, monkeypatch, capsys, argv, setup, expected_command, output_text
):
    monkeypatch.chdir(initialized_project)
    _configure_agent_backend(initialized_project)

    if setup == "write":
        chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        (chapter_dir / "outline.md").write_text(
            "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
            encoding="utf-8",
        )

    def fake_run(command, *, cwd, capture_output, text, encoding):
        payload = load_config(initialized_project / ".pizhi" / "config.yaml")
        assert payload.execution.backend == "agent"
        request_payload = Path(cwd, "agent_request.json").read_text(encoding="utf-8")
        assert expected_command in request_payload
        Path(cwd, "agent_output.md").write_text(output_text, encoding="utf-8")
        return CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_run)

    exit_code = main(argv)
    captured = capsys.readouterr()

    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"
    run_id = _extract_run_id(captured.out)
    record = RunStore(runs_dir).load(run_id)

    assert exit_code == 0
    assert record.metadata["backend"] == "agent"
    assert record.metadata["agent_backend"] == "opencode"
    assert record.run_dir.joinpath("agent_task.md").exists()
    assert record.run_dir.joinpath("agent_request.json").exists()
    assert record.run_dir.joinpath("agent_output.md").exists()


def _extract_run_id(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("Run ID: "):
            return line.removeprefix("Run ID: ").strip()
    raise AssertionError("missing Run ID output")
