from pathlib import Path
import subprocess

import pytest

import scripts.verification.e2e_claude_opencode as e2e_claude_opencode
from scripts.verification.e2e_claude_opencode import StageConfig
from scripts.verification.e2e_claude_opencode import StageExecutionResult
from scripts.verification.e2e_claude_opencode import collect_stage_artifacts
from scripts.verification.e2e_claude_opencode import build_stage_config
from scripts.verification.e2e_claude_opencode import build_stage_report_path
from scripts.verification.e2e_claude_opencode import build_validation_root_path
from scripts.verification.e2e_claude_opencode import build_validation_root_name
from scripts.verification.e2e_claude_opencode import invoke_claude_stage
from scripts.verification.e2e_claude_opencode import main
from scripts.verification.e2e_claude_opencode import collect_host_pizhi_outputs
from scripts.verification.e2e_claude_opencode import render_claude_stage_prompt
from scripts.verification.e2e_claude_opencode import render_stage_report
from scripts.verification.e2e_claude_opencode import run_stage


def test_build_validation_root_name_is_timestamped_and_stable():
    root_name = build_validation_root_name("2026-04-22T12:34:56")
    assert root_name == "pizhi-e2e-claude-opencode-2026-04-22T12-34-56"


def test_build_stage_config_for_smoke_stage():
    config = build_stage_config("stage1", report_date="2026-04-22")
    assert config.slug == "stage1"
    assert config.target_chapters == 3
    assert config.report_path.name == "2026-04-22-e2e-stage-1-smoke.md"


def test_build_validation_root_path_uses_tmp_base_and_root_name():
    path = build_validation_root_path("2026-04-22T12:34:56")
    assert path == Path("tmp") / "pizhi-e2e-claude-opencode-2026-04-22T12-34-56"


def test_build_stage_report_path_uses_report_date_and_docs_dir():
    path = build_stage_report_path(
        "stage2",
        report_date="2026-05-01",
        docs_dir=Path("artifacts") / "verification",
    )
    assert path == Path("artifacts") / "verification" / "2026-05-01-e2e-stage-2-endurance.md"


def test_build_stage_config_rejects_unknown_stage_slug():
    with pytest.raises(ValueError, match="unknown stage slug"):
        build_stage_config("stage9", report_date="2026-04-22")


def test_render_claude_stage_prompt_mentions_agents_playbook():
    prompt = render_claude_stage_prompt(
        stage_slug="stage1",
        project_root="C:/tmp/project",
        repo_root="C:/repo/Pizhi",
        target_chapters=3,
        genre="urban fantasy",
    )
    assert "agents/pizhi/AGENTS.md" in prompt
    assert "repo/playbook are read-only" in prompt
    assert "only modify the temp project" in prompt
    assert "pizhi continue run --count" in prompt
    assert "review --full" in prompt
    assert "compile" in prompt
    assert "Once you reach the target chapters" in prompt
    assert "stage-end review" in prompt
    assert "stop" in prompt.lower()
    assert "stage1" in prompt
    assert "C:/tmp/project" in prompt
    assert "C:/repo/Pizhi" in prompt
    assert "3" in prompt
    assert "urban fantasy" in prompt
    assert "${stage_slug}" not in prompt
    assert "${project_root}" not in prompt
    assert "${repo_root}" not in prompt
    assert "${target_chapters}" not in prompt
    assert "${genre}" not in prompt


def test_collect_stage_artifacts_indexes_buckets_with_stable_absolute_paths(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    cache_root = project_root / ".pizhi" / "cache"
    runs_dir = cache_root / "runs"
    sessions_dir = cache_root / "continue_sessions"
    checkpoints_dir = cache_root / "checkpoints"
    manuscript_dir = project_root / "manuscript"

    runs_dir.mkdir(parents=True)
    sessions_dir.mkdir(parents=True)
    checkpoints_dir.mkdir(parents=True)
    manuscript_dir.mkdir(parents=True)

    (runs_dir / "run-b.json").write_text("run-b", encoding="utf-8")
    (runs_dir / "run-a.json").write_text("run-a", encoding="utf-8")
    (sessions_dir / "session-2.json").write_text("session-2", encoding="utf-8")
    (sessions_dir / "session-1.json").write_text("session-1", encoding="utf-8")
    (checkpoints_dir / "checkpoint-2.json").write_text("checkpoint-2", encoding="utf-8")
    (checkpoints_dir / "checkpoint-1.json").write_text("checkpoint-1", encoding="utf-8")
    (cache_root / "review_full.md").write_text("review", encoding="utf-8")
    (manuscript_dir / "vol_2.md").write_text("vol-2", encoding="utf-8")
    (manuscript_dir / "vol_1.md").write_text("vol-1", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    relative_data = collect_stage_artifacts(Path("project"))
    absolute_data = collect_stage_artifacts(project_root)

    expected_keys = ["runs", "sessions", "checkpoints", "reports", "manuscript"]
    assert list(relative_data.keys()) == expected_keys
    assert relative_data == absolute_data

    assert relative_data["runs"] == [
        (runs_dir / "run-a.json").resolve().as_posix(),
        (runs_dir / "run-b.json").resolve().as_posix(),
    ]
    assert relative_data["sessions"] == [
        (sessions_dir / "session-1.json").resolve().as_posix(),
        (sessions_dir / "session-2.json").resolve().as_posix(),
    ]
    assert relative_data["checkpoints"] == [
        (checkpoints_dir / "checkpoint-1.json").resolve().as_posix(),
        (checkpoints_dir / "checkpoint-2.json").resolve().as_posix(),
    ]
    assert relative_data["reports"] == [
        (cache_root / "review_full.md").resolve().as_posix(),
    ]
    assert relative_data["manuscript"] == [
        (manuscript_dir / "vol_1.md").resolve().as_posix(),
        (manuscript_dir / "vol_2.md").resolve().as_posix(),
    ]


def test_render_claude_stage_prompt_reports_missing_template_clearly(tmp_path, monkeypatch):
    monkeypatch.setattr(
        e2e_claude_opencode,
        "_CLAUDE_STAGE_PROMPT_TEMPLATE_PATH",
        tmp_path / "missing" / "claude_stage_prompt.md",
    )

    with pytest.raises(RuntimeError, match="unable to load Claude stage prompt template"):
        render_claude_stage_prompt(
            stage_slug="stage1",
            project_root="C:/tmp/project",
            repo_root="C:/repo/Pizhi",
            target_chapters=3,
            genre="urban fantasy",
        )


def test_invoke_claude_stage_strips_heading_from_rendered_prompt(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    repo_root = tmp_path / "repo"
    project_root.mkdir()
    repo_root.mkdir()
    observed: dict[str, object] = {}

    def fake_subprocess_run(command, **kwargs):
        observed["command"] = command
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    monkeypatch.setattr(e2e_claude_opencode, "subprocess", type("FakeSubprocess", (), {"run": staticmethod(fake_subprocess_run)}))
    monkeypatch.setattr(
        e2e_claude_opencode,
        "shutil",
        type("FakeShutil", (), {"which": staticmethod(lambda _name: "C:/tools/claude.cmd")}),
    )
    monkeypatch.setattr(e2e_claude_opencode, "_current_report_date", lambda: "2026-04-22")
    monkeypatch.setattr(
        e2e_claude_opencode,
        "render_claude_stage_prompt",
        lambda **_: "# Claude Stage Prompt\n\nStep 1\nStep 2",
    )
    monkeypatch.setattr(e2e_claude_opencode, "collect_stage_artifacts", lambda _: {})
    monkeypatch.setattr(e2e_claude_opencode, "collect_host_pizhi_outputs", lambda *_args, **_kwargs: [])

    invoke_claude_stage(
        stage_slug="stage1",
        project_root=project_root,
        repo_root=repo_root,
        genre="urban fantasy",
    )

    assert observed["command"][-1].endswith("Step 1\nStep 2")
    assert "# Claude Stage Prompt" not in observed["command"][-1]


def test_render_stage_report_contains_summary_and_artifact_index():
    report = render_stage_report(
        stage_name="Stage 1",
        project_root="C:/tmp/project",
        command_log=["pizhi status", "pizhi review --full", "pizhi compile --chapter 1"],
        pizhi_outputs=[
            ("pizhi status", "Project healthy."),
            ("pizhi review --full", "Review report generated."),
        ],
        artifact_index={
            "runs": ["run-1"],
            "sessions": ["session-1"],
            "checkpoints": ["checkpoint-1"],
        },
        outcome_summary="Stage completed.",
    )
    assert "Stage 1" in report
    assert "run-1" in report
    assert "checkpoint-1" in report
    assert "Stage completed." in report
    assert "Project healthy." in report
    assert "Review report generated." in report


def test_invoke_claude_stage_runs_expected_subprocess_surface(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    repo_root = tmp_path / "repo"
    playbook_root = repo_root / "agents" / "pizhi"
    project_root.mkdir()
    repo_root.mkdir()
    observed: dict[str, object] = {}
    resolved_command = Path("C:/tools/claude.cmd")

    def fake_subprocess_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=command,
            returncode=4,
            stdout="claude stdout\n",
            stderr="claude stderr\n",
        )

    monkeypatch.setattr(e2e_claude_opencode, "subprocess", type("FakeSubprocess", (), {"run": staticmethod(fake_subprocess_run)}))
    monkeypatch.setattr(
        e2e_claude_opencode,
        "shutil",
        type("FakeShutil", (), {"which": staticmethod(lambda name: str(resolved_command) if name == "claude" else None)}),
    )
    monkeypatch.setattr(e2e_claude_opencode, "_current_report_date", lambda: "2026-04-22")
    monkeypatch.setattr(e2e_claude_opencode, "render_claude_stage_prompt", lambda **_: "rendered prompt")
    monkeypatch.setattr(e2e_claude_opencode, "collect_stage_artifacts", lambda _: {"runs": ["run-1"]})
    monkeypatch.setattr(
        e2e_claude_opencode,
        "collect_host_pizhi_outputs",
        lambda *_args, **_kwargs: [("pizhi review --full", "review output")],
    )

    result = invoke_claude_stage(
        stage_slug="stage1",
        project_root=project_root,
        repo_root=repo_root,
        genre="urban fantasy",
        command_log=["pizhi status"],
    )

    assert observed["command"] == [
        str(resolved_command),
        "--permission-mode",
        "bypassPermissions",
        "--add-dir",
        str(playbook_root.resolve()),
        "-p",
        (
            "Execute the following validation task exactly as written. "
            "Treat it as your active assignment, not as a prompt template to discuss. "
            "Do not ask for clarification before starting.\n\nrendered prompt"
        ),
    ]
    assert observed["kwargs"] == {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "check": False,
        "cwd": project_root.resolve(),
    }
    assert result.command_log == [
        "pizhi status",
        "claude --permission-mode bypassPermissions --add-dir <repo_root>/agents/pizhi -p <rendered prompt>",
    ]
    assert result.pizhi_outputs == [("pizhi review --full", "review output")]
    assert result.returncode == 4
    assert result.claude_stdout == "claude stdout"
    assert result.claude_stderr == "claude stderr"


def test_run_stage_writes_report_and_preserves_execution_result(tmp_path, monkeypatch):
    report_path = tmp_path / "docs" / "verification" / "stage-report.md"
    project_root = tmp_path / "project"
    project_root.mkdir()
    execution_result = StageExecutionResult(
        stage_name="Stage 1",
        project_root=project_root.resolve(),
        command_log=["pizhi status", "claude -p <rendered prompt>"],
        pizhi_outputs=[("pizhi review --full", "review output")],
        artifact_index={"runs": ["run-1"]},
        outcome_summary="Stage failed cleanly.",
        claude_stdout="stdout text",
        claude_stderr="stderr text",
        returncode=9,
        report_path=None,
    )

    monkeypatch.setattr(
        e2e_claude_opencode,
        "build_stage_config",
        lambda *_args, **_kwargs: StageConfig(slug="stage1", target_chapters=3, report_path=report_path),
    )
    monkeypatch.setattr(e2e_claude_opencode, "invoke_claude_stage", lambda **_kwargs: execution_result)

    result = run_stage(
        stage_slug="stage1",
        project_root=project_root,
        repo_root="C:/repo/Pizhi",
        genre="urban fantasy",
        report_date="2026-04-22",
    )

    assert result.returncode == 9
    assert result.report_path == report_path
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "Stage failed cleanly." in report_text
    assert "review output" in report_text
    assert "stderr text" in report_text


def test_run_stage_anchors_report_output_to_repo_root(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo" / "Pizhi"
    project_root = tmp_path / "project"
    repo_root.mkdir(parents=True)
    project_root.mkdir()
    observed: dict[str, object] = {}
    execution_result = StageExecutionResult(
        stage_name="Stage 1",
        project_root=project_root.resolve(),
        command_log=[],
        pizhi_outputs=[],
        artifact_index={},
        outcome_summary="done",
        claude_stdout="",
        claude_stderr="",
        returncode=0,
    )

    def fake_build_stage_config(stage_slug, report_date, docs_dir=None):
        observed["stage_slug"] = stage_slug
        observed["report_date"] = report_date
        observed["docs_dir"] = docs_dir
        return StageConfig(
            slug=stage_slug,
            target_chapters=3,
            report_path=Path(docs_dir) / "2026-04-22-e2e-stage-1-smoke.md",
        )

    monkeypatch.setattr(e2e_claude_opencode, "build_stage_config", fake_build_stage_config)
    monkeypatch.setattr(e2e_claude_opencode, "invoke_claude_stage", lambda **_kwargs: execution_result)

    result = run_stage(
        stage_slug="stage1",
        project_root=project_root,
        repo_root=repo_root,
        genre="urban fantasy",
        report_date="2026-04-22",
    )

    assert observed["docs_dir"] == repo_root / "docs" / "verification"
    assert result.report_path == repo_root / "docs" / "verification" / "2026-04-22-e2e-stage-1-smoke.md"


def test_collect_host_pizhi_outputs_prefers_highest_numbered_manuscript(tmp_path):
    project_root = tmp_path / "project"
    manuscript_dir = project_root / "manuscript"
    manuscript_dir.mkdir(parents=True)
    earlier = manuscript_dir / "vol_2.md"
    later = manuscript_dir / "vol_10.md"
    earlier.write_text("volume two", encoding="utf-8")
    later.write_text("volume ten", encoding="utf-8")

    outputs = collect_host_pizhi_outputs(
        project_root,
        artifact_index={
            "reports": [],
            "manuscript": [earlier.resolve().as_posix(), later.resolve().as_posix()],
        },
    )

    assert outputs == [("pizhi compile", "volume ten")]


def test_main_defaults_project_root_for_stage_entrypoint_and_returns_exit_code(tmp_path, monkeypatch, capsys):
    repo_root = tmp_path / "noval" / "Pizhi" / ".worktrees" / "e2e-claude-opencode-validation"
    repo_root.mkdir(parents=True)
    captured: dict[str, object] = {}

    monkeypatch.setattr(e2e_claude_opencode, "_current_timestamp", lambda: "2026-04-22T12:34:56")

    def fake_run_stage(**kwargs):
        captured.update(kwargs)
        captured["project_root_exists"] = Path(kwargs["project_root"]).exists()
        return StageExecutionResult(
            stage_name="Stage 1",
            project_root=Path(kwargs["project_root"]).resolve(),
            command_log=[],
            pizhi_outputs=[],
            artifact_index={},
            outcome_summary="done",
            claude_stdout="",
            claude_stderr="",
            returncode=6,
            report_path=tmp_path / "docs" / "verification" / "report.md",
        )

    monkeypatch.setattr(e2e_claude_opencode, "run_stage", fake_run_stage)

    exit_code = main(["--stage", "stage1", "--repo-root", repo_root.as_posix()])

    assert exit_code == 6
    assert Path(captured["project_root"]) == (
        tmp_path / "noval" / "tmp" / "pizhi-e2e-claude-opencode-2026-04-22T12-34-56"
    )
    assert captured["project_root_exists"] is True
    assert captured["repo_root"] == repo_root.as_posix()
    assert captured["genre"] == "urban fantasy"
    assert capsys.readouterr().out.strip() == (tmp_path / "docs" / "verification" / "report.md").as_posix()
