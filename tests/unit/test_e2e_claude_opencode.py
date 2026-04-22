from pathlib import Path

import pytest

from scripts.verification.e2e_claude_opencode import collect_stage_artifacts
from scripts.verification.e2e_claude_opencode import build_stage_config
from scripts.verification.e2e_claude_opencode import build_stage_report_path
from scripts.verification.e2e_claude_opencode import build_validation_root_path
from scripts.verification.e2e_claude_opencode import build_validation_root_name
from scripts.verification.e2e_claude_opencode import render_claude_stage_prompt


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


def test_collect_stage_artifacts_reads_runs_sessions_and_checkpoints(tmp_path):
    data = collect_stage_artifacts(tmp_path)
    assert set(data.keys()) >= {"runs", "sessions", "checkpoints", "reports"}
