from pathlib import Path
import subprocess

import pytest

import scripts.verification.e2e_claude_opencode as e2e_claude_opencode
from scripts.verification.e2e_claude_opencode import StageConfig
from scripts.verification.e2e_claude_opencode import StageExecutionResult
from scripts.verification.e2e_claude_opencode import collect_stage_artifacts
from scripts.verification.e2e_claude_opencode import build_stage_config
from scripts.verification.e2e_claude_opencode import build_stage_report_path
from scripts.verification.e2e_claude_opencode import build_stage_watchdog_issues
from scripts.verification.e2e_claude_opencode import build_validation_root_path
from scripts.verification.e2e_claude_opencode import build_validation_root_name
from scripts.verification.e2e_claude_opencode import evaluate_stage_outcome
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
    assert "AGENTS.md" in prompt
    assert "resources/workflow.md" in prompt
    assert "resources/commands.md" in prompt
    assert "repo/playbook are read-only" in prompt
    assert "Only modify the temp project" in prompt
    assert "Do not directly edit `.pizhi/`, `manuscript/`, chapter source files, or `meta.json`." in prompt
    assert "Do not stop after reading files" in prompt
    assert "Do not reply with a plan first" in prompt
    assert "pizhi continue run --count" in prompt
    assert "review --full" in prompt
    assert "compile" in prompt
    assert "Stage success conditions" in prompt
    assert "Execute this validation stage now" in prompt
    assert "stage1" in prompt
    assert "C:/tmp/project" in prompt
    assert "C:/repo/Pizhi" in prompt
    assert "C:/repo/Pizhi/agents/pizhi" in prompt
    assert "3" in prompt
    assert "urban fantasy" in prompt
    assert "${stage_slug}" not in prompt
    assert "${project_root}" not in prompt
    assert "${repo_root}" not in prompt
    assert "${playbook_root}" not in prompt
    assert "${target_chapters}" not in prompt
    assert "${genre}" not in prompt


def test_render_claude_stage_prompt_uses_playbook_relative_paths():
    prompt = render_claude_stage_prompt(
        stage_slug="stage1",
        project_root="C:/tmp/project",
        repo_root="C:/repo/Pizhi",
        target_chapters=3,
        genre="urban fantasy",
    )
    assert "C:/repo/Pizhi/agents/pizhi/AGENTS.md" in prompt
    assert "C:/repo/Pizhi/agents/pizhi/resources/workflow.md" in prompt
    assert "C:/repo/Pizhi/agents/pizhi/resources/commands.md" in prompt
    assert "`agents/pizhi/AGENTS.md`" not in prompt
    assert "`agents/pizhi/resources/workflow.md`" not in prompt
    assert "`agents/pizhi/resources/commands.md`" not in prompt


def test_render_claude_stage_prompt_states_stage_deliverables_explicitly():
    prompt = render_claude_stage_prompt(
        stage_slug="stage1",
        project_root="C:/tmp/project",
        repo_root="C:/repo/Pizhi",
        target_chapters=3,
        genre="urban fantasy",
    )
    assert "Stage success conditions" in prompt
    assert 'pizhi init --project-name "Urban Fantasy Validation"' in prompt
    assert '--genre "urban fantasy"' in prompt
    assert "pizhi agent configure" in prompt
    assert ".pizhi/cache/review_full.md" in prompt
    assert "manuscript/" in prompt
    assert "run/session/checkpoint" in prompt


def test_render_claude_stage_prompt_uses_stage1_command_targets():
    prompt = render_claude_stage_prompt(
        stage_slug="stage1",
        project_root="C:/tmp/project",
        repo_root="C:/repo/Pizhi",
        target_chapters=3,
        genre="urban fantasy",
    )
    assert "pizhi continue run --count 3 --execute" in prompt
    assert "pizhi checkpoints --session-id <session_id>" in prompt
    assert "pizhi review --full" in prompt
    assert "pizhi compile --chapters 1-3" in prompt
    assert "Do not stop after reading files, after `pizhi init`, or after `pizhi status`." in prompt
    assert "If `pizhi review --full` or `pizhi compile --chapters 1-3` fails, report the failure and stop." in prompt
    assert "pizhi brainstorm --execute" in prompt
    assert "pizhi apply --run-id <run_id>" in prompt


def test_render_claude_stage_prompt_overrides_generic_playbook_defaults_for_stage1():
    prompt = render_claude_stage_prompt(
        stage_slug="stage1",
        project_root="C:/tmp/project",
        repo_root="C:/repo/Pizhi",
        target_chapters=3,
        genre="urban fantasy",
    )
    assert "The stage-specific workflow below overrides any generic guidance in the playbook resources." in prompt
    assert "For this stage, the only valid value for `pizhi continue run --count` is `3`." in prompt
    assert "Do not use any other count." in prompt
    assert "The current working directory may be empty before `pizhi init`; this is expected." in prompt
    assert "Do not ask for additional context because this prompt contains the validation context." in prompt


def test_render_claude_stage_prompt_stops_after_first_target_write_checkpoint():
    prompt = render_claude_stage_prompt(
        stage_slug="stage1",
        project_root="C:/tmp/project",
        repo_root="C:/repo/Pizhi",
        target_chapters=3,
        genre="urban fantasy",
    )
    assert "After you apply the write checkpoint for chapters `1-3`, do not run `pizhi continue resume` again." in prompt
    assert "Do not generate or apply checkpoints for chapters outside `1-3`." in prompt
    assert "Treat any failed `pizhi checkpoint apply --id <checkpoint_id>` as a blocking failure." in prompt


def test_render_claude_stage_prompt_describes_batched_continue_flow_for_stage2():
    prompt = render_claude_stage_prompt(
        stage_slug="stage2",
        project_root="C:/tmp/project",
        repo_root="C:/repo/Pizhi",
        target_chapters=10,
        genre="urban fantasy",
    )
    assert "Continue sessions may emit checkpoints in smaller chapter batches instead of the full target range." in prompt
    assert "Do not treat the first `1-3` batch as stage completion for this stage." in prompt
    assert "apply the outline checkpoint for chapters `1-3`" in prompt
    assert "apply the write checkpoint for chapters `4-6`" in prompt
    assert "apply the outline checkpoint for chapters `10-10`" in prompt
    assert "After you apply the write checkpoint for chapters `10-10`, stop the continue loop." in prompt


def test_build_claude_stage_prompts_splits_large_stage_into_initial_resume_and_finalization_prompts():
    prompts = e2e_claude_opencode._build_claude_stage_prompts(
        stage_slug="stage2",
        project_root="C:/tmp/project",
        repo_root="C:/repo/Pizhi",
        playbook_root="C:/repo/Pizhi/agents/pizhi",
        target_chapters=10,
        genre="urban fantasy",
    )

    assert len(prompts) == 5
    assert "Execute only the exact `pizhi` commands listed below, in order." in prompts[0]
    assert "Do not run any other `pizhi` commands." in prompts[0]
    assert "The current working directory may be empty before `pizhi init`; this is expected." in prompts[0]
    assert "Do not ask for additional context because this prompt contains the validation context." in prompts[0]
    assert "Forbidden examples: `pizhi write --chapter" in prompts[0]
    assert "pizhi init --project-name \"Urban Fantasy Validation\"" in prompts[0]
    assert "pizhi brainstorm --execute" in prompts[0]
    assert "pizhi apply --run-id <run_id>" in prompts[0]
    assert "pizhi continue run --count 10 --execute" in prompts[0]
    assert "chapters `1-3`" in prompts[0]
    assert "chapters `4-6`" in prompts[1]
    assert "Resolve `<session_id>` from `pizhi status` or the latest `.pizhi/cache/continue_sessions/*/manifest.json`." in prompts[1]
    assert "Never run a command with the literal `<session_id>` placeholder." in prompts[1]
    assert "Do not stop after applying the outline checkpoint; the step is incomplete until the write checkpoint is applied." in prompts[1]
    assert "Do not run `pizhi review`, do not analyze quality, and do not ask whether to apply fixes in this step." in prompts[1]
    assert "chapters `7-9`" in prompts[2]
    assert "chapters `10-10`" in prompts[3]
    assert "pizhi review --full" in prompts[4]
    assert "pizhi compile --chapters 1-10" in prompts[4]


def test_build_stage_overlay_playbook_contains_stage_specific_commands(tmp_path):
    project_root = tmp_path / "validation" / "project"
    repo_root = tmp_path / "repo"
    project_root.mkdir(parents=True)
    repo_root.mkdir()
    step = e2e_claude_opencode._build_claude_stage_steps(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=repo_root,
        playbook_root=tmp_path / "overlay",
        target_chapters=10,
        genre="urban fantasy",
    )[0]

    overlay_root = e2e_claude_opencode._build_stage_overlay_playbook(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=repo_root,
        target_chapters=10,
        genre="urban fantasy",
        step=step,
    )

    agents_text = (overlay_root / "AGENTS.md").read_text(encoding="utf-8")
    stage_text = (overlay_root / "resources" / "stage.md").read_text(encoding="utf-8")
    commands_text = (overlay_root / "resources" / "allowed-commands.md").read_text(encoding="utf-8")

    assert overlay_root == project_root.parent / "overlay_playbook"
    assert "Stage prompt is the only authority" in agents_text
    assert "Do not read or apply" in agents_text
    assert "workflow.md" in agents_text
    assert "examples.md" in agents_text
    assert "pizhi continue run --count 10 --execute" in commands_text
    assert "pizhi continue run --count 3 --execute" not in commands_text
    assert "<n>" not in commands_text
    assert "Batch range: `1-3`" in stage_text


def test_build_stage_overlay_playbook_resume_step_requires_write_checkpoint_before_stop(tmp_path):
    project_root = tmp_path / "validation" / "project"
    repo_root = tmp_path / "repo"
    project_root.mkdir(parents=True)
    repo_root.mkdir()
    step = e2e_claude_opencode._build_claude_stage_steps(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=repo_root,
        playbook_root=tmp_path / "overlay",
        target_chapters=10,
        genre="urban fantasy",
    )[1]

    overlay_root = e2e_claude_opencode._build_stage_overlay_playbook(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=repo_root,
        target_chapters=10,
        genre="urban fantasy",
        step=step,
    )

    commands_text = (overlay_root / "resources" / "allowed-commands.md").read_text(encoding="utf-8")

    assert "Run `pizhi continue resume --session-id <session_id>` again to generate the write checkpoint" in commands_text
    assert "Do not stop after applying the outline checkpoint." in commands_text
    assert "apply the write checkpoint for chapters `4-6`" in commands_text
    assert "Stop this step after applying the write checkpoint" in commands_text


def test_initial_stage_step_allows_brainstorm_run_generation_and_apply(tmp_path):
    steps = e2e_claude_opencode._build_claude_stage_steps(
        stage_slug="stage2",
        project_root=tmp_path / "project",
        repo_root=tmp_path / "repo",
        playbook_root=tmp_path / "repo" / "agents" / "pizhi",
        target_chapters=10,
        genre="urban fantasy",
    )

    initial_fragments = steps[0].allowed_command_fragments

    assert any("brainstorm" in fragment for fragment in initial_fragments)
    assert any("apply" in fragment and "run-id" in fragment for fragment in initial_fragments)


def test_build_stage_watchdog_issues_flags_blocked_session_and_overshoot(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    session_dir = project_root / ".pizhi" / "cache" / "continue_sessions" / "session-1"
    session_dir.mkdir(parents=True)
    (session_dir / "manifest.json").write_text(
        """{
  "session_id": "session-1",
  "count": 10,
  "direction": "",
  "start_chapter": 1,
  "target_end_chapter": 10,
  "current_stage": "write",
  "current_range": [1, 3],
  "last_checkpoint_id": "checkpoint-1",
  "status": "blocked",
  "created_at": "2026-04-22T00:00:00Z",
  "updated_at": "2026-04-22T00:15:00Z"
}""",
        encoding="utf-8",
    )
    index_path = project_root / ".pizhi" / "chapters" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        '{"n": 1, "status": "drafted"}\n{"n": 4, "status": "drafted"}\n',
        encoding="utf-8",
    )
    step = e2e_claude_opencode._build_claude_stage_steps(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=tmp_path / "repo",
        playbook_root=tmp_path / "repo" / "agents" / "pizhi",
        target_chapters=10,
        genre="urban fantasy",
    )[0]
    monkeypatch.setattr(e2e_claude_opencode, "_list_running_process_commandlines", lambda: [])

    issues = build_stage_watchdog_issues(project_root=project_root, stage_slug="stage2", step=step)

    assert any("session session-1 is blocked" in issue for issue in issues)
    assert any("chapters beyond ch003 advanced unexpectedly" in issue for issue in issues)


def test_build_stage_watchdog_issues_flags_disallowed_direct_write_process(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    step = e2e_claude_opencode._build_claude_stage_steps(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=tmp_path / "repo",
        playbook_root=tmp_path / "repo" / "agents" / "pizhi",
        target_chapters=10,
        genre="urban fantasy",
    )[0]
    monkeypatch.setattr(
        e2e_claude_opencode,
        "_list_running_process_commandlines",
        lambda: ['"C:\\Python\\python.exe" "C:\\Python\\Scripts\\pizhi.exe" write --chapter 5 --execute'],
    )

    issues = build_stage_watchdog_issues(project_root=project_root, stage_slug="stage2", step=step)

    assert any("disallowed running command detected" in issue for issue in issues)


def test_build_stage_watchdog_issues_allows_shell_wrapped_resume_with_stdin_redirect(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    step = e2e_claude_opencode._build_claude_stage_steps(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=tmp_path / "repo",
        playbook_root=tmp_path / "repo" / "agents" / "pizhi",
        target_chapters=10,
        genre="urban fantasy",
    )[0]
    monkeypatch.setattr(
        e2e_claude_opencode,
        "_list_running_process_commandlines",
        lambda: ["bash -lc 'pizhi continue resume --session-id session-1' < /dev/null"],
    )

    issues = build_stage_watchdog_issues(project_root=project_root, stage_slug="stage2", step=step)

    assert not any("disallowed running command detected" in issue for issue in issues)


def test_build_stage_watchdog_issues_flags_stalled_root_process_when_only_conhost_remains(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    step = e2e_claude_opencode._build_claude_stage_steps(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=tmp_path / "repo",
        playbook_root=tmp_path / "repo" / "agents" / "pizhi",
        target_chapters=10,
        genre="urban fantasy",
    )[0]
    monkeypatch.setattr(
        e2e_claude_opencode,
        "_list_running_process_entries",
        lambda root_pid=None: [
            e2e_claude_opencode.ProcessEntry(
                process_id=100,
                parent_process_id=1,
                commandline='python scripts/verification/e2e_claude_opencode.py --stage stage2',
            ),
            e2e_claude_opencode.ProcessEntry(
                process_id=101,
                parent_process_id=100,
                commandline='\\??\\C:\\WINDOWS\\system32\\conhost.exe 0x4',
            ),
        ],
    )

    issues = build_stage_watchdog_issues(
        project_root=project_root,
        stage_slug="stage2",
        step=step,
        root_pid=100,
    )

    assert any("step appears stalled" in issue for issue in issues)


def test_build_stage_watchdog_issues_flags_disallowed_command_chained_after_allowed_one(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    step = e2e_claude_opencode._build_claude_stage_steps(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=tmp_path / "repo",
        playbook_root=tmp_path / "repo" / "agents" / "pizhi",
        target_chapters=10,
        genre="urban fantasy",
    )[0]
    monkeypatch.setattr(
        e2e_claude_opencode,
        "_list_running_process_commandlines",
        lambda: ['"C:\\Python\\Scripts\\pizhi.exe" status && "C:\\Python\\Scripts\\pizhi.exe" write --chapter 5 --execute'],
    )

    issues = build_stage_watchdog_issues(project_root=project_root, stage_slug="stage2", step=step)

    assert any("pizhi write --chapter 5 --execute" in issue for issue in issues)


def test_build_stage_step_state_issues_flags_missing_batch_write_progress(tmp_path):
    project_root = tmp_path / "project"
    index_path = project_root / ".pizhi" / "chapters" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        "\n".join(
            [
                '{"n": 1, "title": "ch1", "status": "drafted"}',
                '{"n": 2, "title": "ch2", "status": "drafted"}',
                '{"n": 3, "title": "ch3", "status": "drafted"}',
            ]
        ),
        encoding="utf-8",
    )
    step = e2e_claude_opencode.ClaudeStageStep(
        prompt="step 4-6",
        prompt_kind="resume",
        batch_range=(4, 6),
        allowed_max_chapter=6,
        allowed_command_fragments=(),
    )

    issues = e2e_claude_opencode.build_stage_step_state_issues(
        project_root=project_root,
        stage_slug="stage2",
        step=step,
    )

    assert any("expected drafted chapters for this step are missing: ch004, ch005, ch006" in issue for issue in issues)


def test_build_stage_step_state_issues_flags_missing_chapter_index_for_batch_step(tmp_path):
    project_root = tmp_path / "project"
    step = e2e_claude_opencode.ClaudeStageStep(
        prompt="step 1-3",
        prompt_kind="initial",
        batch_range=(1, 3),
        allowed_max_chapter=3,
        allowed_command_fragments=(),
    )

    issues = e2e_claude_opencode.build_stage_step_state_issues(
        project_root=project_root,
        stage_slug="stage2",
        step=step,
    )

    assert any("chapter index was not generated for this step" in issue for issue in issues)


def test_build_stage_step_state_issues_accepts_completed_batch_write_progress(tmp_path):
    project_root = tmp_path / "project"
    index_path = project_root / ".pizhi" / "chapters" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        "\n".join(
            [
                '{"n": 4, "title": "ch4", "status": "drafted"}',
                '{"n": 5, "title": "ch5", "status": "drafted"}',
                '{"n": 6, "title": "ch6", "status": "drafted"}',
            ]
        ),
        encoding="utf-8",
    )
    step = e2e_claude_opencode.ClaudeStageStep(
        prompt="step 4-6",
        prompt_kind="resume",
        batch_range=(4, 6),
        allowed_max_chapter=6,
        allowed_command_fragments=(),
    )

    issues = e2e_claude_opencode.build_stage_step_state_issues(
        project_root=project_root,
        stage_slug="stage2",
        step=step,
    )

    assert issues == []


def test_build_stage_watchdog_issues_rejects_allowed_command_with_extra_flags(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    step = e2e_claude_opencode._build_claude_stage_steps(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=tmp_path / "repo",
        playbook_root=tmp_path / "repo" / "agents" / "pizhi",
        target_chapters=10,
        genre="urban fantasy",
    )[-1]
    monkeypatch.setattr(
        e2e_claude_opencode,
        "_list_running_process_commandlines",
        lambda: ['"C:\\Python\\Scripts\\pizhi.exe" review --full --write'],
    )

    issues = build_stage_watchdog_issues(project_root=project_root, stage_slug="stage2", step=step)

    assert any("pizhi review --full --write" in issue for issue in issues)


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


def test_evaluate_stage_outcome_marks_stage1_failed_when_artifacts_overshoot_target(tmp_path):
    project_root = tmp_path / "project"
    index_path = project_root / ".pizhi" / "chapters" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        "\n".join(
            [
                '{"n": 1, "title": "第001章", "vol": 1, "status": "compiled", "updated": "2026-04-22"}',
                '{"n": 2, "title": "第002章", "vol": 1, "status": "compiled", "updated": "2026-04-22"}',
                '{"n": 3, "title": "第003章", "vol": 1, "status": "compiled", "updated": "2026-04-22"}',
                '{"n": 4, "title": "第004章", "vol": 1, "status": "drafted", "updated": "2026-04-22"}',
            ]
        ),
        encoding="utf-8",
    )
    artifact_index = {
        "runs": ["run-1"],
        "sessions": ["session-1"],
        "checkpoints": ["checkpoint-1", "checkpoint-2"],
        "reports": [],
        "manuscript": [],
    }

    effective_returncode, outcome_summary = evaluate_stage_outcome(
        stage_slug="stage1",
        returncode=0,
        artifact_index=artifact_index,
        project_root=project_root,
    )

    assert effective_returncode == 1
    assert "review report was not generated" in outcome_summary
    assert "compiled manuscript output was not generated" in outcome_summary
    assert "chapters beyond 1-3 advanced unexpectedly" in outcome_summary


def test_evaluate_stage_outcome_treats_malformed_index_as_validation_failure(tmp_path):
    project_root = tmp_path / "project"
    index_path = project_root / ".pizhi" / "chapters" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text('{"n": 1, "status": "compiled"}\n{bad json}\n', encoding="utf-8")

    effective_returncode, outcome_summary = evaluate_stage_outcome(
        stage_slug="stage1",
        returncode=0,
        artifact_index={
            "runs": ["run-1"],
            "sessions": ["session-1"],
            "checkpoints": ["checkpoint-1"],
            "reports": ["review_full.md"],
            "manuscript": ["manuscript/ch001-ch003.md"],
        },
        project_root=project_root,
    )

    assert effective_returncode == 1
    assert "chapter index could not be parsed" in outcome_summary


def test_evaluate_stage_outcome_treats_invalid_index_schema_as_validation_failure(tmp_path):
    project_root = tmp_path / "project"
    index_path = project_root / ".pizhi" / "chapters" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        '{"n": 1, "status": "compiled"}\n{"n": "oops", "title": "bad n", "status": "drafted"}\n',
        encoding="utf-8",
    )

    effective_returncode, outcome_summary = evaluate_stage_outcome(
        stage_slug="stage1",
        returncode=0,
        artifact_index={
            "runs": ["run-1"],
            "sessions": ["session-1"],
            "checkpoints": ["checkpoint-1"],
            "reports": ["review_full.md"],
            "manuscript": ["manuscript/ch001-ch003.md"],
        },
        project_root=project_root,
    )

    assert effective_returncode == 1
    assert "chapter index schema is invalid" in outcome_summary


def test_evaluate_stage_outcome_fails_when_latest_matching_session_is_blocked(tmp_path):
    project_root = tmp_path / "project"
    index_path = project_root / ".pizhi" / "chapters" / "index.jsonl"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        "\n".join(
            [
                '{"n": 1, "status": "compiled"}',
                '{"n": 2, "status": "compiled"}',
                '{"n": 3, "status": "compiled"}',
            ]
        ),
        encoding="utf-8",
    )
    session_dir = project_root / ".pizhi" / "cache" / "continue_sessions" / "session-1"
    session_dir.mkdir(parents=True)
    (session_dir / "manifest.json").write_text(
        """{
  "session_id": "session-1",
  "count": 3,
  "direction": "",
  "start_chapter": 1,
  "target_end_chapter": 3,
  "current_stage": "write",
  "current_range": [1, 3],
  "last_checkpoint_id": "checkpoint-1",
  "status": "blocked",
  "created_at": "2026-04-22T00:00:00Z",
  "updated_at": "2026-04-22T00:15:00Z"
}""",
        encoding="utf-8",
    )

    effective_returncode, outcome_summary = evaluate_stage_outcome(
        stage_slug="stage1",
        returncode=0,
        artifact_index={
            "runs": ["run-1"],
            "sessions": ["session-1"],
            "checkpoints": ["checkpoint-1"],
            "reports": ["review_full.md"],
            "manuscript": ["manuscript/ch001-ch003.md"],
        },
        project_root=project_root,
    )

    assert effective_returncode == 1
    assert "session session-1 is blocked" in outcome_summary


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
        str((project_root.parent / "overlay_playbook").resolve()),
        "-p",
        "rendered prompt",
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
        f"claude --permission-mode bypassPermissions --add-dir {(project_root.parent / 'overlay_playbook').resolve()} -p <rendered prompt>",
    ]
    assert result.pizhi_outputs == [("pizhi review --full", "review output")]
    assert result.returncode == 4
    assert result.claude_stdout == "claude stdout"
    assert result.claude_stderr == "claude stderr"


def test_invoke_claude_stage_refuses_to_start_when_single_flight_preflight_fails(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    repo_root = tmp_path / "repo"
    project_root.mkdir()
    repo_root.mkdir()
    observed = {"called": False}

    monkeypatch.setattr(e2e_claude_opencode, "_current_report_date", lambda: "2026-04-22")
    monkeypatch.setattr(e2e_claude_opencode, "collect_stage_artifacts", lambda _: {})
    monkeypatch.setattr(e2e_claude_opencode, "collect_host_pizhi_outputs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        e2e_claude_opencode,
        "build_single_flight_issues",
        lambda **_kwargs: ["another validation chain is still active"],
    )

    def fail_if_step_runs(**_kwargs):
        observed["called"] = True
        raise AssertionError("no Claude step should start when preflight fails")

    monkeypatch.setattr(e2e_claude_opencode, "_run_claude_stage_step", fail_if_step_runs)

    result = invoke_claude_stage(
        stage_slug="stage1",
        project_root=project_root,
        repo_root=repo_root,
        genre="urban fantasy",
    )

    assert observed["called"] is False
    assert result.returncode == 1
    assert "PREFLIGHT:" in result.claude_stderr
    assert "another validation chain is still active" in result.claude_stderr


def test_build_single_flight_issues_matches_windows_backslash_commandlines(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo" / "Pizhi"
    project_root = tmp_path / "tmp" / "pizhi-e2e-claude-opencode-2026-04-22T22-00-00"
    repo_root.mkdir(parents=True)
    project_root.mkdir(parents=True)
    monkeypatch.setattr(e2e_claude_opencode.os, "getpid", lambda: 99999)
    monkeypatch.setattr(
        e2e_claude_opencode,
        "_list_running_process_entries",
        lambda root_pid=None: [
            e2e_claude_opencode.ProcessEntry(
                process_id=1234,
                parent_process_id=1,
                commandline=(
                    f'C:\\WINDOWS\\system32\\cmd.exe /c C:\\tools\\claude.CMD --add-dir '
                    f'{str(repo_root / "agents" / "pizhi")} -p "..."'
                ),
            )
        ],
    )

    issues = e2e_claude_opencode.build_single_flight_issues(
        repo_root=repo_root,
        project_root=project_root,
    )

    assert any("existing Claude playbook process detected" in issue for issue in issues)


def test_build_single_flight_issues_ignores_process_listing_shell_commands(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo" / "Pizhi"
    project_root = tmp_path / "tmp" / "pizhi-e2e-claude-opencode-2026-04-22T22-00-00"
    repo_root.mkdir(parents=True)
    project_root.mkdir(parents=True)
    monkeypatch.setattr(e2e_claude_opencode.os, "getpid", lambda: 99999)
    monkeypatch.setattr(
        e2e_claude_opencode,
        "_list_running_process_entries",
        lambda root_pid=None: [
            e2e_claude_opencode.ProcessEntry(
                process_id=1234,
                parent_process_id=1,
                commandline=(
                    "pwsh.exe -Command \"Get-CimInstance Win32_Process | "
                    "Where-Object { $_.CommandLine -like '*pizhi-opencode-*' }\""
                ),
            )
        ],
    )

    issues = e2e_claude_opencode.build_single_flight_issues(
        repo_root=repo_root,
        project_root=project_root,
    )

    assert issues == []


def test_invoke_claude_stage_runs_batched_prompts_for_large_stage(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    repo_root = tmp_path / "repo"
    project_root.mkdir()
    repo_root.mkdir()
    observed_prompts: list[str] = []
    resolved_command = Path("C:/tools/claude.cmd")

    def fake_subprocess_run(command, **kwargs):
        observed_prompts.append(command[-1])
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=f"stdout-{len(observed_prompts)}\n",
            stderr="",
        )

    def fail_if_rendered(**_kwargs):
        raise AssertionError("large stages should use the batched prompt builder")

    monkeypatch.setattr(e2e_claude_opencode, "subprocess", type("FakeSubprocess", (), {"run": staticmethod(fake_subprocess_run)}))
    monkeypatch.setattr(
        e2e_claude_opencode,
        "shutil",
        type("FakeShutil", (), {"which": staticmethod(lambda name: str(resolved_command) if name == "claude" else None)}),
    )
    monkeypatch.setattr(e2e_claude_opencode, "_current_report_date", lambda: "2026-04-22")
    monkeypatch.setattr(e2e_claude_opencode, "render_claude_stage_prompt", fail_if_rendered)
    monkeypatch.setattr(e2e_claude_opencode, "collect_stage_artifacts", lambda _: {"runs": ["run-1"]})
    monkeypatch.setattr(e2e_claude_opencode, "collect_host_pizhi_outputs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(e2e_claude_opencode, "build_stage_step_state_issues", lambda **_kwargs: [])
    monkeypatch.setattr(e2e_claude_opencode, "evaluate_stage_outcome", lambda **kwargs: (kwargs["returncode"], "ok"))

    result = invoke_claude_stage(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=repo_root,
        genre="urban fantasy",
        command_log=["pizhi status"],
    )

    assert len(observed_prompts) == 5
    assert "pizhi continue run --count 10 --execute" in observed_prompts[0]
    assert "chapters `1-3`" in observed_prompts[0]
    assert "chapters `4-6`" in observed_prompts[1]
    assert "chapters `7-9`" in observed_prompts[2]
    assert "chapters `10-10`" in observed_prompts[3]
    assert "pizhi review --full" in observed_prompts[4]
    assert "pizhi compile --chapters 1-10" in observed_prompts[4]
    assert result.command_log == [
        "pizhi status",
        f"claude --permission-mode bypassPermissions --add-dir {(project_root.parent / 'overlay_playbook').resolve()} -p <rendered prompt>",
        f"claude --permission-mode bypassPermissions --add-dir {(project_root.parent / 'overlay_playbook').resolve()} -p <rendered prompt>",
        f"claude --permission-mode bypassPermissions --add-dir {(project_root.parent / 'overlay_playbook').resolve()} -p <rendered prompt>",
        f"claude --permission-mode bypassPermissions --add-dir {(project_root.parent / 'overlay_playbook').resolve()} -p <rendered prompt>",
        f"claude --permission-mode bypassPermissions --add-dir {(project_root.parent / 'overlay_playbook').resolve()} -p <rendered prompt>",
    ]
    assert result.returncode == 0
    assert result.claude_stdout == "stdout-1\n\nstdout-2\n\nstdout-3\n\nstdout-4\n\nstdout-5"


def test_invoke_claude_stage_stops_before_next_step_when_step_postflight_fails(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    repo_root = tmp_path / "repo"
    project_root.mkdir()
    repo_root.mkdir()
    called_steps: list[str] = []
    steps = [
        e2e_claude_opencode.ClaudeStageStep(
            prompt="step 1",
            prompt_kind="initial",
            batch_range=(1, 3),
            allowed_max_chapter=3,
            allowed_command_fragments=(r"status",),
        ),
        e2e_claude_opencode.ClaudeStageStep(
            prompt="step 2",
            prompt_kind="resume",
            batch_range=(4, 6),
            allowed_max_chapter=6,
            allowed_command_fragments=(r"status",),
        ),
    ]

    monkeypatch.setattr(e2e_claude_opencode, "_current_report_date", lambda: "2026-04-22")
    monkeypatch.setattr(e2e_claude_opencode, "collect_stage_artifacts", lambda _: {"runs": ["run-1"]})
    monkeypatch.setattr(e2e_claude_opencode, "collect_host_pizhi_outputs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(e2e_claude_opencode, "build_single_flight_issues", lambda **_kwargs: [])
    monkeypatch.setattr(e2e_claude_opencode, "_build_claude_stage_steps", lambda **_kwargs: steps)
    monkeypatch.setattr(e2e_claude_opencode, "_resolve_cli_command", lambda _name: "C:/tools/claude.cmd")

    def fake_run_step(**kwargs):
        called_steps.append(kwargs["step"].prompt)
        return subprocess.CompletedProcess(
            args=["claude", "-p", kwargs["step"].prompt],
            returncode=0,
            stdout=f"stdout:{kwargs['step'].prompt}",
            stderr="",
        )

    monkeypatch.setattr(e2e_claude_opencode, "_run_claude_stage_step", fake_run_step)
    monkeypatch.setattr(
        e2e_claude_opencode,
        "build_stage_step_state_issues",
        lambda **kwargs: ["session session-1 is blocked"] if kwargs["step"].prompt == "step 1" else [],
    )
    monkeypatch.setattr(e2e_claude_opencode, "evaluate_stage_outcome", lambda **kwargs: (kwargs["returncode"], "postflight failed"))

    result = invoke_claude_stage(
        stage_slug="stage2",
        project_root=project_root,
        repo_root=repo_root,
        genre="urban fantasy",
    )

    assert called_steps == ["step 1"]
    assert result.returncode == 1
    assert "POSTFLIGHT:" in result.claude_stderr
    assert "session session-1 is blocked" in result.claude_stderr


def test_invoke_claude_stage_aborts_long_running_step_when_watchdog_finds_drift(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    repo_root = tmp_path / "repo"
    project_root.mkdir()
    repo_root.mkdir()
    resolved_command = Path("C:/tools/claude.cmd")

    class FakePopen:
        def __init__(self, command, **kwargs):
            self.args = command
            self.kwargs = kwargs
            self._wait_calls = 0
            self.pid = 123
            self.returncode = None
            kwargs["stdout"].write("partial stdout")
            kwargs["stdout"].flush()
            kwargs["stderr"].write("partial stderr")
            kwargs["stderr"].flush()

        def wait(self, timeout=None):
            self._wait_calls += 1
            if self._wait_calls == 1:
                raise subprocess.TimeoutExpired(cmd=self.args, timeout=timeout)
            return 124 if self.returncode is None else self.returncode

        def kill(self):
            self.returncode = 124

    fake_subprocess = type(
        "FakeSubprocess",
        (),
        {
            "Popen": FakePopen,
            "PIPE": subprocess.PIPE,
            "CompletedProcess": subprocess.CompletedProcess,
            "TimeoutExpired": subprocess.TimeoutExpired,
        },
    )
    monkeypatch.setattr(e2e_claude_opencode, "subprocess", fake_subprocess)
    monkeypatch.setattr(e2e_claude_opencode, "_WATCHDOG_INTERVAL_SECONDS", 1)
    monkeypatch.setattr(
        e2e_claude_opencode,
        "shutil",
        type("FakeShutil", (), {"which": staticmethod(lambda name: str(resolved_command) if name == "claude" else None)}),
    )
    monkeypatch.setattr(e2e_claude_opencode, "_current_report_date", lambda: "2026-04-22")
    monkeypatch.setattr(e2e_claude_opencode, "render_claude_stage_prompt", lambda **_: "rendered prompt")
    monkeypatch.setattr(e2e_claude_opencode, "collect_stage_artifacts", lambda _: {"runs": ["run-1"]})
    monkeypatch.setattr(e2e_claude_opencode, "collect_host_pizhi_outputs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        e2e_claude_opencode,
        "build_stage_watchdog_issues",
        lambda **_kwargs: ["disallowed running command detected: pizhi write --chapter 20 --execute"],
    )
    monkeypatch.setattr(e2e_claude_opencode, "evaluate_stage_outcome", lambda **kwargs: (kwargs["returncode"], "watchdog failed"))

    result = invoke_claude_stage(
        stage_slug="stage1",
        project_root=project_root,
        repo_root=repo_root,
        genre="urban fantasy",
    )

    assert result.returncode == 124
    assert "disallowed running command detected" in result.claude_stderr
    assert "partial stdout" in result.claude_stdout


def test_run_claude_stage_step_collects_output_from_temp_files_after_process_exit(tmp_path, monkeypatch):
    class FakePopen:
        def __init__(self, command, **kwargs):
            self.args = command
            self.kwargs = kwargs
            self.pid = 123
            self.returncode = 0
            assert hasattr(kwargs["stdout"], "write")
            assert hasattr(kwargs["stderr"], "write")
            kwargs["stdout"].write("stdout text")
            kwargs["stdout"].flush()
            kwargs["stderr"].write("stderr text")
            kwargs["stderr"].flush()

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            self.returncode = 124

    fake_subprocess = type(
        "FakeSubprocess",
        (),
        {
            "Popen": FakePopen,
            "PIPE": subprocess.PIPE,
            "CompletedProcess": subprocess.CompletedProcess,
            "TimeoutExpired": subprocess.TimeoutExpired,
        },
    )
    monkeypatch.setattr(e2e_claude_opencode, "subprocess", fake_subprocess)

    completed = e2e_claude_opencode._run_claude_stage_step(
        claude_command="claude",
        playbook_root=tmp_path / "playbook",
        project_root=tmp_path / "project",
        stage_slug="stage2",
        step=e2e_claude_opencode.ClaudeStageStep(
            prompt="rendered prompt",
            prompt_kind="initial",
            batch_range=(1, 3),
            allowed_max_chapter=3,
            allowed_command_fragments=(),
        ),
    )

    assert completed.returncode == 0
    assert completed.stdout == "stdout text"
    assert completed.stderr == "stderr text"


def test_run_claude_stage_step_ignores_capture_dir_cleanup_permission_error(tmp_path, monkeypatch):
    class FakeTempDir:
        def __init__(self, *, ignore_cleanup_errors=False):
            self.ignore_cleanup_errors = ignore_cleanup_errors
            self.path = tmp_path / "capture"

        def __enter__(self):
            self.path.mkdir(exist_ok=True)
            return str(self.path)

        def __exit__(self, exc_type, exc, tb):
            if not self.ignore_cleanup_errors:
                raise PermissionError("capture dir still in use")
            return False

    observed: dict[str, object] = {}

    def fake_tempdir(*, prefix=None, ignore_cleanup_errors=False):
        observed["prefix"] = prefix
        observed["ignore_cleanup_errors"] = ignore_cleanup_errors
        return FakeTempDir(ignore_cleanup_errors=ignore_cleanup_errors)

    class FakePopen:
        def __init__(self, command, **kwargs):
            self.args = command
            self.kwargs = kwargs
            self.pid = 123
            self.returncode = 0
            kwargs["stdout"].write("stdout text")
            kwargs["stdout"].flush()
            kwargs["stderr"].write("stderr text")
            kwargs["stderr"].flush()

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            self.returncode = 124

    fake_subprocess = type(
        "FakeSubprocess",
        (),
        {
            "Popen": FakePopen,
            "PIPE": subprocess.PIPE,
            "CompletedProcess": subprocess.CompletedProcess,
            "TimeoutExpired": subprocess.TimeoutExpired,
        },
    )
    monkeypatch.setattr(e2e_claude_opencode, "subprocess", fake_subprocess)
    monkeypatch.setattr(
        e2e_claude_opencode,
        "tempfile",
        type("FakeTempfile", (), {"TemporaryDirectory": staticmethod(fake_tempdir)}),
    )

    completed = e2e_claude_opencode._run_claude_stage_step(
        claude_command="claude",
        playbook_root=tmp_path / "playbook",
        project_root=tmp_path / "project",
        stage_slug="stage2",
        step=e2e_claude_opencode.ClaudeStageStep(
            prompt="rendered prompt",
            prompt_kind="initial",
            batch_range=(1, 3),
            allowed_max_chapter=3,
            allowed_command_fragments=(),
        ),
    )

    assert observed["prefix"] == "pizhi-claude-stage-step-"
    assert observed["ignore_cleanup_errors"] is True
    assert completed.returncode == 0
    assert completed.stdout == "stdout text"
    assert completed.stderr == "stderr text"


def test_run_claude_stage_step_writes_project_anchor_files_before_invoking_claude(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    observed: dict[str, object] = {}

    class FakePopen:
        def __init__(self, command, **kwargs):
            observed["agents_text"] = (project_root / "AGENTS.md").read_text(encoding="utf-8")
            observed["task_text"] = (project_root / "STAGE_TASK.md").read_text(encoding="utf-8")
            self.args = command
            self.kwargs = kwargs
            self.pid = 123
            self.returncode = 0

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            self.returncode = 124

    fake_subprocess = type(
        "FakeSubprocess",
        (),
        {
            "Popen": FakePopen,
            "PIPE": subprocess.PIPE,
            "CompletedProcess": subprocess.CompletedProcess,
            "TimeoutExpired": subprocess.TimeoutExpired,
        },
    )
    monkeypatch.setattr(e2e_claude_opencode, "subprocess", fake_subprocess)

    completed = e2e_claude_opencode._run_claude_stage_step(
        claude_command="claude",
        playbook_root=tmp_path / "playbook",
        project_root=project_root,
        stage_slug="stage2",
        step=e2e_claude_opencode.ClaudeStageStep(
            prompt="Execute this validation stage now.",
            prompt_kind="initial",
            batch_range=(1, 3),
            allowed_max_chapter=3,
            allowed_command_fragments=(),
        ),
    )

    assert completed.returncode == 0
    assert "This directory is a temporary Pizhi validation project." in observed["agents_text"]
    assert "The project may be empty before `pizhi init`; this is expected." in observed["agents_text"]
    assert "Execute this validation stage now." in observed["task_text"]


def test_run_claude_stage_step_keeps_waiting_after_clean_watchdog_timeout(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    observed = {"killed": False}

    class FakePopen:
        def __init__(self, command, **kwargs):
            self.args = command
            self.kwargs = kwargs
            self.pid = 123
            self.returncode = None
            self.wait_calls = 0
            kwargs["stdout"].write("partial stdout")
            kwargs["stdout"].flush()
            kwargs["stderr"].write("partial stderr")
            kwargs["stderr"].flush()

        def wait(self, timeout=None):
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired(cmd=self.args, timeout=timeout)
            self.returncode = 0
            return self.returncode

        def kill(self):
            observed["killed"] = True
            self.returncode = 124

    fake_subprocess = type(
        "FakeSubprocess",
        (),
        {
            "Popen": FakePopen,
            "PIPE": subprocess.PIPE,
            "CompletedProcess": subprocess.CompletedProcess,
            "TimeoutExpired": subprocess.TimeoutExpired,
        },
    )
    monkeypatch.setattr(e2e_claude_opencode, "subprocess", fake_subprocess)
    monkeypatch.setattr(e2e_claude_opencode, "_WATCHDOG_INTERVAL_SECONDS", 1)
    monkeypatch.setattr(e2e_claude_opencode, "build_stage_watchdog_issues", lambda **_kwargs: [])

    completed = e2e_claude_opencode._run_claude_stage_step(
        claude_command="claude",
        playbook_root=tmp_path / "playbook",
        project_root=project_root,
        stage_slug="stage1",
        step=e2e_claude_opencode.ClaudeStageStep(
            prompt="rendered prompt",
            prompt_kind="single",
            batch_range=(1, 3),
            allowed_max_chapter=3,
            allowed_command_fragments=(),
        ),
    )

    assert completed.returncode == 0
    assert observed["killed"] is False
    assert completed.stdout == "partial stdout"
    assert completed.stderr == "partial stderr"


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
