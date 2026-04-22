from pathlib import Path

import pytest

import scripts.verification.e2e_claude_opencode as e2e_claude_opencode
from scripts.verification.e2e_claude_opencode import collect_stage_artifacts
from scripts.verification.e2e_claude_opencode import build_stage_config
from scripts.verification.e2e_claude_opencode import build_stage_report_path
from scripts.verification.e2e_claude_opencode import build_validation_root_path
from scripts.verification.e2e_claude_opencode import build_validation_root_name
from scripts.verification.e2e_claude_opencode import render_claude_stage_prompt
from scripts.verification.e2e_claude_opencode import render_stage_report


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
    assert "pizhi continue run --count" in prompt
    assert "review --full" in prompt
    assert "compile" in prompt
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


def test_render_stage_report_contains_summary_and_artifact_index():
    report = render_stage_report(
        stage_name="Stage 1",
        project_root="C:/tmp/project",
        command_log=["pizhi status", "pizhi review --full", "pizhi compile --chapter 1"],
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
