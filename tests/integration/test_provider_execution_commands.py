from __future__ import annotations

import pytest

from pizhi.cli import main

from tests.unit.test_provider_execution import StubAdapter
from tests.unit.test_provider_execution import _configure_provider


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

    assert exit_code == 0
    assert "Prepared prompt packet:" in captured.out
    assert "Run ID:" in captured.out
    assert any(path.joinpath("normalized.md").exists() for path in runs_dir.iterdir())


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

    assert exit_code == 0
    assert "Prepared prompt packet:" in captured.out
    assert "Run ID:" in captured.out
    assert any(path.joinpath("normalized.md").exists() for path in runs_dir.iterdir())


def test_write_execute_writes_run_id_and_run_artifacts(initialized_project, monkeypatch, capsys):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    _configure_provider(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StubAdapter("## chapter\n..."),
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

    assert exit_code == 0
    assert "Prepared prompt packet:" in captured.out
    assert "Run ID:" in captured.out
    assert any(path.joinpath("normalized.md").exists() for path in runs_dir.iterdir())


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
