# Pizhi Milestone 7 Provider Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add checkpointed provider-backed orchestration for `continue --execute`, including persistent sessions, persistent checkpoints, checkpoint batch apply, resume, and prompt-budget guards.

**Architecture:** Milestone 7 layers orchestration state on top of milestone 6's run execution instead of replacing it. A continue session owns overall progress, checkpoints own stage-local run groups, and checkpoint apply is the only path that advances truth-source state between outline and write phases.

**Tech Stack:** Python 3.14, pytest, argparse, pathlib, dataclasses, stdlib `json`, existing provider execution services, existing deterministic apply services

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\milestone-7-provider-orchestration`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -v`
  - Observed while writing this plan: `141 passed`

## File Map

- `src/pizhi/core/paths.py`: add cache directory helpers for continue sessions and checkpoints
- `src/pizhi/services/continue_session_store.py`: create/load/update continue session manifests
- `src/pizhi/services/checkpoint_store.py`: create/load/update checkpoint manifests
- `src/pizhi/services/prompt_budget.py`: estimate prompt size, decide outline splitting, and raise bounded budget errors
- `src/pizhi/services/continue_execution.py`: start sessions, generate outline/write checkpoints, resume sessions, and update orchestration state
- `src/pizhi/services/checkpoint_apply_service.py`: batch apply checkpoint runs in deterministic order with all-or-nothing behavior
- `src/pizhi/services/continue_service.py`: keep prompt-only deterministic continue path intact while delegating provider-backed orchestration to new services when needed
- `src/pizhi/services/outline_service.py`: merge split outline checkpoint applies into stable chapter outlines and stable `outline_global.md`
- `src/pizhi/commands/continue_cmd.py`: dispatch prompt-only continue, `continue --execute`, `continue sessions`, and `continue resume`
- `src/pizhi/commands/checkpoint_cmd.py`: implement `checkpoints` listing and `checkpoint apply --id ...`
- `src/pizhi/cli.py`: register new command shapes and flags without regressing existing continue syntax
- `tests/unit/test_continue_session_store.py`: session manifest round-trip and status transition coverage
- `tests/unit/test_checkpoint_store.py`: checkpoint manifest round-trip and ordering coverage
- `tests/unit/test_prompt_budget.py`: outline splitting and write blocking behavior
- `tests/unit/test_continue_execution.py`: session start, checkpoint generation, resume gating, and blocked-state coverage
- `tests/unit/test_checkpoint_apply_service.py`: deterministic apply ordering and all-or-nothing behavior
- `tests/integration/test_continue_execute_command.py`: command-level provider-backed continue flow
- `tests/integration/test_checkpoint_commands.py`: session listing, checkpoint listing, checkpoint apply, and resume flow
- `docs/superpowers/plans/2026-04-19-pizhi-milestone-7-provider-orchestration.md`: mark verification results after execution

### Task 1: Add Continue Session And Checkpoint Stores

**Files:**
- Modify: `src/pizhi/core/paths.py`
- Create: `src/pizhi/services/continue_session_store.py`
- Create: `src/pizhi/services/checkpoint_store.py`
- Test: `tests/unit/test_continue_session_store.py`
- Test: `tests/unit/test_checkpoint_store.py`

- [x] **Step 1: Write the failing store tests**

```python
def test_continue_session_store_round_trips_manifest(tmp_path):
    store = ContinueSessionStore(tmp_path / ".pizhi" / "cache" / "continue_sessions")
    record = store.create(
        count=6,
        direction="push Shen deeper into the dock war",
        start_chapter=11,
        target_end_chapter=16,
        current_stage="outline",
        current_range=(11, 13),
        status="waiting_apply",
    )

    loaded = store.load(record.session_id)
    assert loaded.session_id == record.session_id
    assert loaded.current_stage == "outline"
    assert loaded.current_range == (11, 13)


def test_checkpoint_store_persists_run_ids_and_status(tmp_path):
    store = CheckpointStore(tmp_path / ".pizhi" / "cache" / "checkpoints")
    record = store.create(
        session_id="session-001",
        stage="write",
        chapter_range=(11, 13),
        run_ids=["run-a", "run-b", "run-c"],
        status="generated",
    )

    loaded = store.load(record.checkpoint_id)
    assert loaded.run_ids == ("run-a", "run-b", "run-c")
    assert loaded.status == "generated"
```

- [x] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_continue_session_store.py tests/unit/test_checkpoint_store.py -v`

Expected:
- import errors because the stores do not exist yet

- [x] **Step 3: Implement path helpers and manifest stores**

```python
@dataclass(frozen=True, slots=True)
class ContinueSessionRecord:
    session_id: str
    session_dir: Path
    manifest_path: Path
    count: int
    direction: str
    start_chapter: int
    target_end_chapter: int
    current_stage: str
    current_range: tuple[int, int]
    last_checkpoint_id: str | None
    status: str
    created_at: str
    updated_at: str
```

```python
@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    checkpoint_id: str
    checkpoint_dir: Path
    manifest_path: Path
    session_id: str
    stage: str
    chapter_range: tuple[int, int]
    run_ids: tuple[str, ...]
    status: str
    created_at: str
    applied_at: str | None
```

```python
class ProjectPaths:
    ...
    @property
    def continue_sessions_dir(self) -> Path:
        return self.cache_dir / "continue_sessions"

    @property
    def checkpoints_dir(self) -> Path:
        return self.cache_dir / "checkpoints"
```

- [x] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_continue_session_store.py tests/unit/test_checkpoint_store.py -v`

Expected: all selected tests `PASSED`

- [x] **Step 5: Commit**

```bash
git add src/pizhi/core/paths.py src/pizhi/services/continue_session_store.py src/pizhi/services/checkpoint_store.py tests/unit/test_continue_session_store.py tests/unit/test_checkpoint_store.py
git commit -m "feat: add continue session and checkpoint stores"
```

### Task 2: Add Prompt Budget Guard And Outline Split Planner

**Files:**
- Create: `src/pizhi/services/prompt_budget.py`
- Test: `tests/unit/test_prompt_budget.py`

- [x] **Step 1: Write the failing budget tests**

```python
def test_outline_budget_splits_three_chapter_request_into_two_plus_one():
    planner = OutlineBatchPlanner(max_prompt_chars=100)
    prompts = {
        11: "x" * 40,
        12: "x" * 40,
        13: "x" * 40,
    }

    batches = planner.plan([11, 12, 13], lambda n: prompts[n])
    assert batches == [(11, 12), (13, 13)]


def test_write_budget_rejects_single_chapter_prompt_that_exceeds_limit():
    with pytest.raises(PromptBudgetError, match="write prompt exceeds budget"):
        ensure_write_prompt_within_budget(chapter_number=11, prompt_text="x" * 1001, max_prompt_chars=1000)
```

- [x] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_prompt_budget.py -v`

Expected:
- import errors because the budget module does not exist yet

- [x] **Step 3: Implement budget estimation and outline splitting**

```python
class PromptBudgetError(ValueError):
    pass


def estimate_prompt_size(prompt_text: str) -> int:
    return len(prompt_text)


def ensure_write_prompt_within_budget(*, chapter_number: int, prompt_text: str, max_prompt_chars: int) -> None:
    if estimate_prompt_size(prompt_text) > max_prompt_chars:
        raise PromptBudgetError(f"write prompt exceeds budget for ch{chapter_number:03d}")
```

```python
class OutlineBatchPlanner:
    def plan(self, chapter_numbers: list[int], prompt_for_chapter) -> list[tuple[int, int]]:
        if _fits(chapter_numbers):
            return [(chapter_numbers[0], chapter_numbers[-1])]
        if len(chapter_numbers) == 3 and _fits(chapter_numbers[:2]) and _fits(chapter_numbers[2:]):
            return [(chapter_numbers[0], chapter_numbers[1]), (chapter_numbers[2], chapter_numbers[2])]
        return [(chapter, chapter) for chapter in chapter_numbers]
```

- [x] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_prompt_budget.py -v`

Expected: all selected tests `PASSED`

- [x] **Step 5: Commit**

```bash
git add src/pizhi/services/prompt_budget.py tests/unit/test_prompt_budget.py
git commit -m "feat: add prompt budget guards for continue orchestration"
```

### Task 3: Build Continue Execution Orchestration

**Files:**
- Create: `src/pizhi/services/continue_execution.py`
- Modify: `src/pizhi/services/continue_service.py`
- Test: `tests/unit/test_continue_execution.py`

- [x] **Step 1: Write the failing orchestration tests**

```python
def test_start_continue_execution_creates_outline_checkpoint(initialized_project, monkeypatch):
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr("pizhi.services.provider_execution.build_provider_adapter", lambda *_: StubAdapter("## ch001 | 标题\n- beat"))

    result = start_continue_execution(initialized_project, count=3, direction="push the dock war")

    assert result.session.status == "waiting_apply"
    assert result.checkpoint.stage == "outline"
    assert result.checkpoint.status == "generated"


def test_resume_continue_execution_requires_ready_to_resume(initialized_project):
    store = ContinueSessionStore(project_paths(initialized_project).continue_sessions_dir)
    session = store.create(..., status="waiting_apply")

    with pytest.raises(ValueError, match="not ready to resume"):
        resume_continue_execution(initialized_project, session.session_id)
```

- [x] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_continue_execution.py -v`

Expected:
- import errors because the orchestration service does not exist yet

- [x] **Step 3: Implement session start and resume orchestration**

```python
def start_continue_execution(project_root: Path, *, count: int, direction: str) -> ContinueExecutionResult:
    chapter_range = ContinueService(project_root)._determine_chapter_range(count)
    session = session_store.create(
        count=count,
        direction=direction,
        start_chapter=chapter_range[0],
        target_end_chapter=chapter_range[1],
        current_stage="outline",
        current_range=_first_checkpoint_range(chapter_range),
        status="running",
    )
    checkpoint = _generate_outline_checkpoint(project_root, session)
    session = session_store.update(
        session.session_id,
        status="waiting_apply",
        last_checkpoint_id=checkpoint.checkpoint_id,
    )
    return ContinueExecutionResult(session=session, checkpoint=checkpoint)
```

```python
def resume_continue_execution(project_root: Path, session_id: str) -> ContinueExecutionResult:
    session = session_store.load(session_id)
    if session.status != "ready_to_resume":
        raise ValueError(f"session {session_id} is not ready to resume")
    if session.current_stage == "outline":
        checkpoint = _generate_write_checkpoint(project_root, session)
    else:
        checkpoint = _advance_to_next_outline_or_complete(project_root, session)
    ...
```

- [x] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_continue_execution.py -v`

Expected: all selected tests `PASSED`

- [x] **Step 5: Commit**

```bash
git add src/pizhi/services/continue_execution.py src/pizhi/services/continue_service.py tests/unit/test_continue_execution.py
git commit -m "feat: add checkpointed continue execution"
```

### Task 4: Add Checkpoint Batch Apply Service

**Files:**
- Create: `src/pizhi/services/checkpoint_apply_service.py`
- Modify: `src/pizhi/services/outline_service.py`
- Test: `tests/unit/test_checkpoint_apply_service.py`

- [x] **Step 1: Write the failing batch-apply tests**

```python
def test_apply_checkpoint_applies_runs_in_chapter_order(initialized_project, monkeypatch):
    checkpoint = _seed_generated_write_checkpoint(initialized_project, run_ids=["run-2", "run-1"])
    applied: list[str] = []
    monkeypatch.setattr("pizhi.services.checkpoint_apply_service.apply_run", lambda root, run_id: applied.append(run_id))

    apply_checkpoint(initialized_project, checkpoint.checkpoint_id)
    assert applied == ["run-1", "run-2"]


def test_apply_checkpoint_stops_after_first_failure_and_blocks_session(initialized_project, monkeypatch):
    checkpoint = _seed_generated_write_checkpoint(initialized_project, run_ids=["run-1", "run-2"])

    def _apply(root, run_id):
        if run_id == "run-1":
            raise ValueError("bad run")

    monkeypatch.setattr("pizhi.services.checkpoint_apply_service.apply_run", _apply)

    with pytest.raises(ValueError, match="bad run"):
        apply_checkpoint(initialized_project, checkpoint.checkpoint_id)

    assert CheckpointStore(...).load(checkpoint.checkpoint_id).status == "failed"
    assert ContinueSessionStore(...).load(checkpoint.session_id).status == "blocked"


def test_apply_split_outline_checkpoint_preserves_all_outline_blocks(initialized_project):
    checkpoint = _seed_generated_outline_checkpoint(
        initialized_project,
        run_ids=["run-outline-011-012", "run-outline-013-013"],
    )

    apply_checkpoint(initialized_project, checkpoint.checkpoint_id)

    outline_global = (initialized_project / ".pizhi" / "global" / "outline_global.md").read_text(encoding="utf-8")
    assert "## ch011 |" in outline_global
    assert "## ch012 |" in outline_global
    assert "## ch013 |" in outline_global


def test_apply_checkpoint_rejects_non_generated_checkpoint(initialized_project):
    checkpoint = _seed_failed_checkpoint(initialized_project, status="failed")

    with pytest.raises(ValueError, match="cannot be applied"):
        apply_checkpoint(initialized_project, checkpoint.checkpoint_id)
```

- [x] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_checkpoint_apply_service.py -v`

Expected:
- import errors because the apply service does not exist yet

- [x] **Step 3: Implement checkpoint batch apply**

```python
def apply_checkpoint(project_root: Path, checkpoint_id: str) -> CheckpointApplyResult:
    checkpoint = checkpoint_store.load(checkpoint_id)
    if checkpoint.status != "generated":
        raise ValueError(f"checkpoint {checkpoint_id} status {checkpoint.status} cannot be applied")
    ordered_run_ids = _sorted_run_ids(project_root, checkpoint.run_ids)
    applied_run_ids: list[str] = []
    try:
        for run_id in ordered_run_ids:
            apply_run(project_root, run_id)
            applied_run_ids.append(run_id)
    except Exception:
        checkpoint_store.mark_failed(checkpoint_id)
        session_store.mark_blocked(checkpoint.session_id)
        raise
    checkpoint_store.mark_applied(checkpoint_id)
    session_store.mark_ready_to_resume(checkpoint.session_id)
    return CheckpointApplyResult(...)
```

```python
class OutlineService:
    ...
    def apply_blocks(self, blocks: list[OutlineBlock], *, merge_global_outline: bool = True) -> None:
        ...
        if merge_global_outline:
            existing_blocks = self.load_existing_blocks()
            merged_blocks = _merge_outline_blocks(existing_blocks, blocks)
            self.write_global_outline(merged_blocks)
```

- [x] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_checkpoint_apply_service.py -v`

Expected: all selected tests `PASSED`

- [x] **Step 5: Commit**

```bash
git add src/pizhi/services/checkpoint_apply_service.py src/pizhi/services/outline_service.py tests/unit/test_checkpoint_apply_service.py
git commit -m "feat: add checkpoint batch apply service"
```

### Task 5: Wire Continue And Checkpoint CLI Commands

**Files:**
- Modify: `src/pizhi/cli.py`
- Modify: `src/pizhi/commands/continue_cmd.py`
- Create: `src/pizhi/commands/checkpoint_cmd.py`
- Test: `tests/integration/test_continue_execute_command.py`
- Test: `tests/integration/test_checkpoint_commands.py`

- [x] **Step 1: Write the failing integration tests for command flows**

```python
def test_continue_execute_creates_session_and_outline_checkpoint(initialized_project, monkeypatch):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    _configure_provider(initialized_project)
    monkeypatch.setattr("pizhi.services.provider_execution.build_provider_adapter", lambda *_: OutlineStubAdapter())

    exit_code = main(["continue", "--count", "3", "--execute"])
    assert exit_code == 0
    assert any((initialized_project / ".pizhi" / "cache" / "continue_sessions").iterdir())


def test_checkpoint_apply_then_resume_advances_session(initialized_project, monkeypatch):
    session_id, checkpoint_id = _seed_generated_outline_checkpoint(initialized_project)

    assert main(["checkpoint", "apply", "--id", checkpoint_id]) == 0
    assert main(["continue", "resume", "--session-id", session_id]) == 0


def test_continue_sessions_and_checkpoints_list_expected_fields(initialized_project, monkeypatch, capsys):
    session_id, checkpoint_id = _seed_generated_outline_checkpoint(initialized_project)

    assert main(["continue", "sessions"]) == 0
    sessions_output = capsys.readouterr().out
    assert session_id in sessions_output
    assert "waiting_apply" in sessions_output

    assert main(["checkpoints", "--session-id", session_id]) == 0
    checkpoints_output = capsys.readouterr().out
    assert checkpoint_id in checkpoints_output
    assert "outline" in checkpoints_output
```

- [x] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_continue_execute_command.py tests/integration/test_checkpoint_commands.py -v`

Expected:
- CLI parsing failures because the new continue and checkpoint command forms do not exist yet

- [x] **Step 3: Implement CLI dispatch and command handlers**

```python
continue_parser = subparsers.add_parser("continue", help="continue outlining and writing chapters")
continue_subparsers = continue_parser.add_subparsers(dest="continue_command")

continue_run_parser = continue_subparsers.add_parser("run", help="continue chapters")
continue_run_parser.add_argument("--count", required=True, type=int)
continue_run_parser.add_argument("--direction")
continue_run_parser.add_argument("--execute", action="store_true")
continue_run_parser.add_argument("--outline-response-file")
continue_run_parser.add_argument("--chapter-responses-dir")

continue_sessions_parser = continue_subparsers.add_parser("sessions", help="list continue sessions")
continue_resume_parser = continue_subparsers.add_parser("resume", help="resume an applied continue session")
continue_resume_parser.add_argument("--session-id", required=True)
```

```python
def run_continue(args: argparse.Namespace) -> int:
    if args.continue_command == "sessions":
        return run_continue_sessions(args)
    if args.continue_command == "resume":
        return run_continue_resume(args)
    if args.continue_command in (None, "run") and args.execute:
        return run_continue_execute(args)
    return run_continue_prompt_only(args)
```

```python
def normalize_legacy_continue_argv(argv: Sequence[str]) -> list[str]:
    if len(argv) >= 1 and argv[0] == "continue":
        if len(argv) == 1 or argv[1].startswith("-"):
            return ["continue", "run", *argv[1:]]
    return list(argv)
```

```python
checkpoint_parser = subparsers.add_parser("checkpoint", help="inspect and apply continue checkpoints")
checkpoint_subparsers = checkpoint_parser.add_subparsers(dest="checkpoint_command")
checkpoint_apply_parser = checkpoint_subparsers.add_parser("apply", help="apply a generated checkpoint")
checkpoint_apply_parser.add_argument("--id", required=True)

checkpoints_parser = subparsers.add_parser("checkpoints", help="list checkpoints for a continue session")
checkpoints_parser.add_argument("--session-id", required=True)
```

- [x] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/integration/test_continue_execute_command.py tests/integration/test_checkpoint_commands.py -v`

Expected: all selected tests `PASSED`

- [x] **Step 5: Commit**

```bash
git add src/pizhi/cli.py src/pizhi/commands/continue_cmd.py src/pizhi/commands/checkpoint_cmd.py tests/integration/test_continue_execute_command.py tests/integration/test_checkpoint_commands.py
git commit -m "feat: add provider-backed continue orchestration commands"
```

### Task 6: Verify Budget Splitting, Blocking, And Prompt-Only Regression

**Files:**
- Modify: `tests/unit/test_continue_execution.py`
- Modify: `tests/integration/test_continue_execute_command.py`

- [x] **Step 1: Add regression tests for outline splitting, write blocking, and prompt-only continue**

```python
def test_continue_execution_splits_outline_checkpoint_when_three_chapter_prompt_exceeds_budget(...):
    ...
    assert checkpoint.run_ids == ("run-outline-11-12", "run-outline-13")


def test_continue_execute_blocks_session_when_single_write_prompt_exceeds_budget(...):
    ...
    assert session.status == "blocked"
    assert "write prompt exceeds budget" in result.stderr


def test_continue_execution_blocks_session_on_provider_failure(...):
    ...
    assert session.status == "blocked"
    assert checkpoint.status == "failed"


def test_continue_execution_blocks_session_on_normalize_failure(...):
    ...
    assert session.status == "blocked"
    assert checkpoint.status == "failed"


def test_continue_prompt_only_flow_is_unchanged_without_execute(initialized_project, fixture_text):
    ...
    assert result.returncode == 0
    assert "Continued chapters" in result.stdout
```

- [x] **Step 2: Run the targeted regression tests to verify they fail**

Run:
`python -m pytest tests/unit/test_continue_execution.py tests/integration/test_continue_execute_command.py -v`

Expected:
- new tests fail because splitting/blocking or prompt-only compatibility is incomplete

- [x] **Step 3: Implement the missing regression behavior**

```python
outline_batches = planner.plan(chapter_numbers, prompt_for_outline_batch)
for batch_range in outline_batches:
    execution = execute_prompt_request(...)
    if execution.status != "succeeded":
        checkpoint_store.mark_failed(checkpoint.checkpoint_id)
        session_store.mark_blocked(session.session_id)
        raise ValueError(...)
```

```python
if not args.execute and args.continue_command in (None, "run"):
    result = service.continue_project(...)
    print(f"Continued chapters ch{start:03d}-ch{end:03d}")
    return 0
```

- [x] **Step 4: Run the targeted regression tests again**

Run:
`python -m pytest tests/unit/test_continue_execution.py tests/integration/test_continue_execute_command.py -v`

Expected: all selected tests `PASSED`

- [x] **Step 5: Commit**

```bash
git add tests/unit/test_continue_execution.py tests/integration/test_continue_execute_command.py src/pizhi/services/continue_execution.py src/pizhi/commands/continue_cmd.py
git commit -m "fix: harden continue orchestration budget handling"
```

### Task 7: Final Verification And Plan State Update

**Files:**
- Modify: `docs/superpowers/plans/2026-04-19-pizhi-milestone-7-provider-orchestration.md`

- [x] **Step 1: Run command smoke tests**

Run:
- `python -m pizhi continue --help`
- `python -m pizhi checkpoints --help`
- `python -m pizhi checkpoint apply --help`

Expected: all commands exit `0`

Observed:
- `python -m pizhi continue --help` -> exit `0`
- `python -m pizhi checkpoints --help` -> exit `0`
- `python -m pizhi checkpoint apply --help` -> exit `0`

- [x] **Step 2: Run the full test suite**

Run:
`python -m pytest tests/unit tests/integration -v`

Expected: all tests `PASSED` and count increases beyond the 141-test baseline

Observed:
- `python -m pytest tests/unit tests/integration -v` -> `188 passed`

- [x] **Step 3: Mark verification steps complete in this plan**

Update this file so the executed verification boxes are checked and add final observed command/test results near Task 7.

- [x] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-19-pizhi-milestone-7-provider-orchestration.md
git commit -m "docs: record milestone 7 verification state"
```
