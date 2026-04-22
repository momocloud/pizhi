# E2E Claude + Opencode Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable validation harness and execute a real-host end-to-end urban-fantasy novel run through `Claude Code -> agents/pizhi -> Pizhi CLI -> opencode`, with staged reports for 3, 10, and 30 chapters.

**Architecture:** Add a small repository-owned verification harness that creates a temporary project, invokes `claude` in non-interactive mode with the repository playbook and the temporary project directory in scope, and archives stage reports plus artifact indexes under `docs/verification/`. Keep the generated novel project outside Git, but make the execution method and results reproducible and versioned.

**Tech Stack:** Python CLI (`pizhi`), Python verification helper, PowerShell invocation, `claude` CLI, `opencode`, pytest, Markdown reports

---

## File Structure

### New files

- `scripts/verification/e2e_claude_opencode.py`
  - Main verification harness.
  - Creates validation roots.
  - Initializes temp novel projects.
  - Invokes `claude` with the correct directories and prompt.
  - Collects stage artifacts and renders report data.
- `scripts/verification/templates/claude_stage_prompt.md`
  - Prompt template handed to `Claude Code` for one validation stage.
  - Encodes the workflow boundary: load `agents/pizhi/`, inspect status, drive `continue`, auto-apply, run `review --full`, run `compile`, stop only when the stage objective is reached or the system becomes impossible to continue.
- `tests/unit/test_e2e_claude_opencode.py`
  - Unit tests for harness config, prompt rendering, temp directory naming, and artifact index extraction.
- `docs/verification/2026-04-22-e2e-stage-1-smoke.md`
  - Stage 1 report, created from the real run.
- `docs/verification/2026-04-22-e2e-stage-2-endurance.md`
  - Stage 2 report, created from the real run.
- `docs/verification/2026-04-22-e2e-stage-3-full-run.md`
  - Stage 3 report, created from the real run.
- `docs/verification/2026-04-22-e2e-claude-opencode-summary.md`
  - Final summary that links all stage reports and records the overall conclusion.

### Existing files to read/reference

- `agents/pizhi/AGENTS.md`
- `agents/pizhi/resources/workflow.md`
- `agents/pizhi/resources/commands.md`
- `agents/pizhi/resources/failure-recovery.md`
- `README.md`
- `docs/verification/2026-04-22-e2e-claude-opencode-validation-design.md`

### Existing files likely unchanged

- Product code under `src/pizhi/`
- Existing tests outside the new verification harness test file

---

### Task 1: Build the verification harness skeleton

**Files:**
- Create: `scripts/verification/e2e_claude_opencode.py`
- Create: `tests/unit/test_e2e_claude_opencode.py`
- Reference: `docs/verification/2026-04-22-e2e-claude-opencode-validation-design.md`

- [ ] **Step 1: Write the failing test for validation root naming and stage config**

```python
from scripts.verification.e2e_claude_opencode import build_stage_config
from scripts.verification.e2e_claude_opencode import build_validation_root_name


def test_build_validation_root_name_is_timestamped_and_stable():
    root_name = build_validation_root_name("2026-04-22T12:34:56")
    assert root_name.startswith("pizhi-e2e-claude-opencode-")


def test_build_stage_config_for_smoke_stage():
    config = build_stage_config("stage1")
    assert config.slug == "stage1"
    assert config.target_chapters == 3
    assert config.report_path.name == "2026-04-22-e2e-stage-1-smoke.md"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
```

Expected:

- FAIL with missing module or missing functions

- [ ] **Step 3: Implement the minimal harness skeleton**

Implement:

- `StageConfig` dataclass
- `build_validation_root_name()`
- `build_stage_config()`
- minimal path helpers for temp roots and report paths

- [ ] **Step 4: Run the unit test to verify it passes**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/verification/e2e_claude_opencode.py tests/unit/test_e2e_claude_opencode.py
git commit -m "Add E2E validation harness skeleton"
```

---

### Task 2: Add Claude host prompt rendering and artifact indexing

**Files:**
- Modify: `scripts/verification/e2e_claude_opencode.py`
- Create: `scripts/verification/templates/claude_stage_prompt.md`
- Modify: `tests/unit/test_e2e_claude_opencode.py`
- Reference: `agents/pizhi/AGENTS.md`
- Reference: `agents/pizhi/resources/workflow.md`
- Reference: `agents/pizhi/resources/commands.md`

- [ ] **Step 1: Write the failing tests for prompt rendering and artifact index extraction**

```python
from scripts.verification.e2e_claude_opencode import collect_stage_artifacts
from scripts.verification.e2e_claude_opencode import render_claude_stage_prompt


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
```

Expected:

- FAIL on unimplemented prompt or artifact helpers

- [ ] **Step 3: Implement prompt rendering and artifact collection**

Implement:

- a reusable prompt template loader
- placeholder substitution for stage target, temp project root, and repo root
- artifact enumeration for:
  - `.pizhi/cache/runs/`
  - `.pizhi/cache/continue_sessions/`
  - `.pizhi/cache/checkpoints/`
  - `.pizhi/cache/review_full.md`
  - `manuscript/`

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/verification/e2e_claude_opencode.py scripts/verification/templates/claude_stage_prompt.md tests/unit/test_e2e_claude_opencode.py
git commit -m "Add Claude stage prompt and artifact indexing"
```

---

### Task 3: Add stage execution and report rendering

**Files:**
- Modify: `scripts/verification/e2e_claude_opencode.py`
- Modify: `tests/unit/test_e2e_claude_opencode.py`
- Reference: `README.md`
- Reference: `docs/verification/2026-04-22-e2e-claude-opencode-validation-design.md`

- [ ] **Step 1: Write the failing tests for report rendering**

```python
from scripts.verification.e2e_claude_opencode import render_stage_report


def test_render_stage_report_contains_summary_and_artifact_index():
    report = render_stage_report(
        stage_name="Stage 1",
        project_root="C:/tmp/project",
        command_log=["pizhi status", "pizhi review --full", "pizhi compile --chapter 1"],
        artifact_index={"runs": ["run-1"], "sessions": ["session-1"], "checkpoints": ["checkpoint-1"]},
        outcome_summary="Stage completed.",
    )
    assert "Stage 1" in report
    assert "run-1" in report
    assert "checkpoint-1" in report
    assert "Stage completed." in report
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
```

Expected:

- FAIL for missing report renderer

- [ ] **Step 3: Implement stage execution helpers and report rendering**

Implement:

- `invoke_claude_stage()` helper that shells out to `claude -p`
- report rendering helper
- output capture for:
  - `claude` stdout/stderr
  - important `pizhi` outputs emitted by the host-driven run
- report file writing into `docs/verification/`

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/verification/e2e_claude_opencode.py tests/unit/test_e2e_claude_opencode.py
git commit -m "Add stage execution and report rendering"
```

---

### Task 4: Execute Stage 1 smoke and archive the report

**Files:**
- Create: `docs/verification/2026-04-22-e2e-stage-1-smoke.md`
- Modify: `scripts/verification/e2e_claude_opencode.py` (only if a real validation bug in the harness is discovered)
- Reference: `agents/pizhi/AGENTS.md`

- [ ] **Step 1: Run Stage 1 with the verification harness**

Run:

```bash
python scripts/verification/e2e_claude_opencode.py --stage stage1
```

Expected:

- a temporary project root is created under `tmp/`
- `claude` drives the project through the playbook
- the stage writes a report to `docs/verification/2026-04-22-e2e-stage-1-smoke.md`

- [ ] **Step 2: Manually inspect the stage report and project outputs**

Check:

- report includes command summary
- report includes session/checkpoint/run indexes
- `.pizhi/cache/review_full.md` exists in the temp project
- `manuscript/` contains compiled output

- [ ] **Step 3: If the stage exposed a harness bug, fix the harness and re-run Stage 1**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
python scripts/verification/e2e_claude_opencode.py --stage stage1
```

Expected:

- PASS for harness tests
- Stage 1 report updated with the successful rerun

- [ ] **Step 4: Commit the Stage 1 artifacts**

```bash
git add docs/verification/2026-04-22-e2e-stage-1-smoke.md scripts/verification/e2e_claude_opencode.py tests/unit/test_e2e_claude_opencode.py
git commit -m "Archive Stage 1 E2E validation"
```

---

### Task 5: Execute Stage 2 endurance and archive the report

**Files:**
- Create: `docs/verification/2026-04-22-e2e-stage-2-endurance.md`
- Modify: `scripts/verification/e2e_claude_opencode.py` (only if harness fixes are needed)
- Modify: `tests/unit/test_e2e_claude_opencode.py` (only if harness fixes are needed)

- [ ] **Step 1: Run Stage 2**

Run:

```bash
python scripts/verification/e2e_claude_opencode.py --stage stage2
```

Expected:

- a 10-chapter temp project run completes or reaches a clearly recorded blocking failure
- report is written to `docs/verification/2026-04-22-e2e-stage-2-endurance.md`

- [ ] **Step 2: Inspect review, compile, and artifact summary**

Check:

- stage report clearly states chapter count achieved
- `review --full` outcome is recorded
- `compile` outcome is recorded
- run/session/checkpoint indexes are present

- [ ] **Step 3: If harness issues were found, fix them with tests first and re-run Stage 2**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
python scripts/verification/e2e_claude_opencode.py --stage stage2
```

Expected:

- PASS for harness tests
- Stage 2 report updated with the rerun

- [ ] **Step 4: Commit the Stage 2 artifacts**

```bash
git add docs/verification/2026-04-22-e2e-stage-2-endurance.md scripts/verification/e2e_claude_opencode.py tests/unit/test_e2e_claude_opencode.py
git commit -m "Archive Stage 2 E2E validation"
```

---

### Task 6: Execute Stage 3 full run and archive the report

**Files:**
- Create: `docs/verification/2026-04-22-e2e-stage-3-full-run.md`
- Modify: `scripts/verification/e2e_claude_opencode.py` (only if harness fixes are needed)
- Modify: `tests/unit/test_e2e_claude_opencode.py` (only if harness fixes are needed)

- [ ] **Step 1: Run Stage 3**

Run:

```bash
python scripts/verification/e2e_claude_opencode.py --stage stage3
```

Expected:

- the 30-chapter validation run completes, or the report clearly documents where it stopped
- report is written to `docs/verification/2026-04-22-e2e-stage-3-full-run.md`

- [ ] **Step 2: Inspect the final stage report**

Check:

- final chapter count is stated
- review and compile status are stated
- blocking / major / minor findings are classified
- artifact index is sufficient to reproduce or inspect the run

- [ ] **Step 3: If harness issues were found, fix them with tests first and re-run Stage 3**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
python scripts/verification/e2e_claude_opencode.py --stage stage3
```

Expected:

- PASS for harness tests
- Stage 3 report updated with the rerun

- [ ] **Step 4: Commit the Stage 3 artifacts**

```bash
git add docs/verification/2026-04-22-e2e-stage-3-full-run.md scripts/verification/e2e_claude_opencode.py tests/unit/test_e2e_claude_opencode.py
git commit -m "Archive Stage 3 E2E validation"
```

---

### Task 7: Write the final summary and run full regression

**Files:**
- Create: `docs/verification/2026-04-22-e2e-claude-opencode-summary.md`
- Modify: `docs/verification/2026-04-22-e2e-stage-1-smoke.md` (only if cross-links are needed)
- Modify: `docs/verification/2026-04-22-e2e-stage-2-endurance.md` (only if cross-links are needed)
- Modify: `docs/verification/2026-04-22-e2e-stage-3-full-run.md` (only if cross-links are needed)
- Modify: `scripts/verification/e2e_claude_opencode.py` (only if report polish is needed)
- Modify: `tests/unit/test_e2e_claude_opencode.py` (only if harness polish is needed)

- [ ] **Step 1: Write the final summary report**

Include:

- overall verdict
- what passed
- what failed
- where artifact evidence lives
- whether the shipped stack is ready for sustained real-host use

- [ ] **Step 2: Run harness tests**

Run:

```bash
python -m pytest tests/unit/test_e2e_claude_opencode.py -q --tb=short -rfE
```

Expected:

- PASS

- [ ] **Step 3: Run the full project regression**

Run:

```bash
python -m pytest tests/unit tests/integration -q --tb=short -rfE
```

Expected:

- PASS

- [ ] **Step 4: Commit the final verification closure**

```bash
git add docs/verification/2026-04-22-e2e-claude-opencode-summary.md docs/verification/2026-04-22-e2e-stage-1-smoke.md docs/verification/2026-04-22-e2e-stage-2-endurance.md docs/verification/2026-04-22-e2e-stage-3-full-run.md scripts/verification/e2e_claude_opencode.py scripts/verification/templates/claude_stage_prompt.md tests/unit/test_e2e_claude_opencode.py
git commit -m "Close E2E Claude opencode validation"
```

---

## Notes for Execution

- Keep the generated novel project outside Git under `tmp/`.
- Do not hand-edit `.pizhi/` in the temp project.
- Do not silently change prompts or configuration mid-stage. If the harness or workflow changes, record it in the relevant stage report.
- Use the repository-shipped playbook as the source of truth for host-side workflow.
- Prefer the existing quiet regression command for all Python test runs:

```bash
python -m pytest tests/unit tests/integration -q --tb=short -rfE
```
