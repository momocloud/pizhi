# Pizhi Milestone 7 Provider Orchestration Design

## Goal

Extend provider-backed execution from single commands into the main writing orchestration path by adding checkpointed `continue --execute` sessions that pause every three chapters, require explicit checkpoint apply, and resume only from applied truth-source state.

## Scope

- Add provider-backed orchestration for `continue --execute`
- Introduce persistent continue sessions and persistent checkpoints
- Add checkpoint-level batch apply with fixed ordering and all-or-nothing behavior
- Add resume flow for paused continue sessions
- Add query commands for continue sessions and checkpoints
- Add prompt-budget guards and outline auto-splitting for provider-backed continue execution

## Non-Goals

- B-class AI semantic review
- Automatic apply after checkpoint generation
- `continue resume` with a new `--direction`
- Multi-provider support
- Smart semantic context compression or dynamic summarization
- Reworking the existing deterministic `continue` workflow

## Primary Decisions

### 1. `continue --execute` is checkpointed, not fire-and-forget

Provider-backed continue execution pauses every three chapters and requires explicit user confirmation through checkpoint apply before continuing.

Checkpoints are true control boundaries, not passive summaries.

### 2. Every next step must be built from applied truth-source state

The next stage may not continue from candidate provider output that has not been applied to the project.

This means:

- after an outline checkpoint is generated, those outline runs must be applied before any write checkpoint starts
- after a write checkpoint is generated, those write runs must be applied before the next chapter group starts

### 3. Checkpoints are two-stage

Each three-chapter group runs in two separate phases:

1. outline checkpoint
2. write checkpoint

This preserves the architecture principle that write generation should depend on confirmed outline truth, not on unconfirmed candidate output.

### 4. Session and checkpoint state must be persisted explicitly

Milestone 7 should not reconstruct orchestration state by inferring from run directories alone.

Instead, it introduces two explicit persisted layers:

- continue session manifests
- checkpoint manifests

These are the truth-source records for orchestration progress, recovery, and resume gating.

### 5. Apply stays explicit but gets a checkpoint-level batch path

Single-run apply from milestone 6 remains available through `pizhi apply --run-id ...`.

Milestone 7 adds checkpoint-level batch apply because a continue checkpoint naturally contains multiple runs and should be applied in a stable, ordered unit.

### 6. Context-budget control is part of orchestration safety

Provider-backed continue execution must guard against oversized prompts.

Milestone 7 does not solve this with semantic compression. Instead it uses:

- write as one-chapter-per-request only
- prompt budget estimation before provider execution
- automatic outline batch splitting when necessary
- explicit blocking when a request still exceeds the configured limit

## Design

### 1. CLI surface

Milestone 7 adds five user-facing orchestration commands or subcommands.

#### Provider-backed continue execution

Add:

- `pizhi continue --count N --execute [--direction "..."]`

This starts a new continue session, generates the first checkpoint, writes its manifests, and pauses.

It does not auto-apply and does not auto-continue past the checkpoint.

#### Continue session listing

Add:

- `pizhi continue sessions`

This lists recent continue sessions with enough metadata to safely choose a session for resume.

Recommended fields:

- `session_id`
- `chapter_range`
- `status`
- `current_stage`
- `last_checkpoint_id`
- `created_at`

#### Checkpoint listing

Add:

- `pizhi checkpoints --session-id <session_id>`

This lists checkpoints for a session in stage order.

Recommended fields:

- `checkpoint_id`
- `session_id`
- `stage`
- `chapter_range`
- `status`
- `created_at`

#### Checkpoint-level batch apply

Add:

- `pizhi checkpoint apply --id <checkpoint_id>`

This applies the checkpoint's runs in deterministic order. The behavior is all-or-nothing:

- runs are applied in fixed order
- if one apply fails, remaining runs are not applied
- checkpoint status becomes `failed`
- session status becomes `blocked`

#### Session resume

Add:

- `pizhi continue resume --session-id <session_id>`

This only works when the session is in `ready_to_resume`.

It does not accept a new `--direction`. Resume continues the original session contract.

### 2. Session and checkpoint persistence

Milestone 7 adds two persistent orchestration stores.

#### Continue session layout

Store sessions under:

- `.pizhi/cache/continue_sessions/<session_id>/manifest.json`

Recommended fields:

- `session_id`
- `count`
- `direction`
- `start_chapter`
- `target_end_chapter`
- `current_stage`
- `current_range`
- `last_checkpoint_id`
- `status`
- `created_at`
- `updated_at`

Recommended statuses:

- `running`
- `waiting_apply`
- `ready_to_resume`
- `blocked`
- `completed`
- `failed`

#### Checkpoint layout

Store checkpoints under:

- `.pizhi/cache/checkpoints/<checkpoint_id>/manifest.json`

Recommended fields:

- `checkpoint_id`
- `session_id`
- `stage`
- `chapter_range`
- `run_ids`
- `status`
- `created_at`
- `applied_at`

Recommended statuses:

- `generated`
- `applied`
- `failed`

### 3. Orchestration state machine

The orchestration flow should be explicit and bounded.

#### Start

`continue --execute`:

1. creates a new session
2. chooses the first chapter group
3. generates the first checkpoint
4. writes checkpoint and session manifests
5. sets session status to `waiting_apply`

#### Apply

`checkpoint apply --id ...`:

1. loads the checkpoint
2. applies runs in fixed order
3. if all succeed:
   - checkpoint -> `applied`
   - session -> `ready_to_resume`
4. if any apply fails:
   - checkpoint -> `failed`
   - session -> `blocked`

#### Resume

`continue resume --session-id ...`:

1. requires session status `ready_to_resume`
2. advances to the next stage or next chapter group
3. generates the next checkpoint
4. sets session back to `waiting_apply`
5. once all requested work is complete:
   - session -> `completed`

### 4. Two-stage checkpoint execution

Each three-chapter group executes as two independent checkpoints.

#### Outline checkpoint

- generate provider-backed outline runs for the selected chapter range
- persist the checkpoint
- stop and wait for checkpoint apply

Apply order:

- ascending chapter number

#### Write checkpoint

Only after the outline checkpoint has been applied:

- generate provider-backed write runs for the same chapter range
- persist the checkpoint
- stop and wait for checkpoint apply

Apply order:

- ascending chapter number

This preserves deterministic truth-source progression across the batch.

### 5. Relationship to milestone 6 run execution

Milestone 7 does not replace the single-command provider path.

Instead it layers orchestration on top of the existing milestone 6 primitives:

- outline request building
- write request building
- provider execution service
- run store
- apply service

Milestone 7 adds:

- continue session store
- checkpoint store
- continue execution orchestration
- checkpoint batch apply service

### 6. Context-budget and splitting rules

Provider context limits are part of the milestone 7 design.

#### Write requests

- always execute one chapter per request
- continue using the existing chapter-context assembly
- perform prompt-budget estimation before provider execution
- if the write prompt exceeds budget, do not execute
- instead:
  - fail the current checkpoint
  - block the session
  - report a readable error identifying the chapter

Milestone 7 does not do automatic summarization or silent truncation for write prompts.

#### Outline requests

- default to one provider request for the three-chapter checkpoint
- estimate prompt size before execution
- if it exceeds the budget:
  - split into `2 + 1`
  - if still too large, split into `1 + 1 + 1`
- these sub-requests still belong to one outline checkpoint

If a single chapter outline request still exceeds budget:

- fail the checkpoint
- block the session
- report a readable error

#### Budget estimation

Milestone 7 should not introduce a heavy tokenizer dependency.

Use a stable approximate budget guard, such as character or word count, driven by configuration defaults or orchestration constants.

This is sufficient for this milestone because the goal is bounded behavior, not provider-specific token optimization.

### 7. Failure handling

Failure handling must remain explicit and recoverable.

#### Provider failure or normalization failure inside checkpoint generation

- reuse milestone 6 run semantics
- checkpoint generation fails
- session becomes `blocked` or remains blocked from further progress
- no apply is allowed for incomplete checkpoints

#### Budget overflow

- if outline can split smaller, split and continue
- if it cannot split smaller, checkpoint fails and session blocks
- if write exceeds budget, checkpoint fails and session blocks immediately

#### Checkpoint apply failure

- stop immediately
- remaining runs in that checkpoint are not applied
- checkpoint -> `failed`
- session -> `blocked`

#### Resume preconditions not met

`continue resume --session-id ...` must reject:

- unknown session id
- session not in `ready_to_resume`
- session already completed

### 8. Backward compatibility

Milestone 7 must preserve the current milestone 1-6 behavior.

Specifically:

- existing deterministic `continue` remains unchanged when `--execute` is not used
- milestone 6 single-command execution remains unchanged
- `apply --run-id ...` remains valid and independent
- maintenance still lives on the deterministic apply side

## Files

Expected new files:

- `src/pizhi/services/continue_session_store.py`
- `src/pizhi/services/checkpoint_store.py`
- `src/pizhi/services/continue_execution.py`
- `src/pizhi/services/checkpoint_apply_service.py`
- `src/pizhi/commands/checkpoint_cmd.py`
- `tests/unit/test_continue_session_store.py`
- `tests/unit/test_checkpoint_store.py`
- `tests/unit/test_continue_execution.py`
- `tests/unit/test_checkpoint_apply_service.py`
- `tests/integration/test_continue_execute_command.py`
- `tests/integration/test_checkpoint_commands.py`

Expected modified files:

- `src/pizhi/cli.py`
- `src/pizhi/commands/continue_cmd.py`
- `src/pizhi/services/continue_service.py`
- `src/pizhi/services/outline_service.py`
- `src/pizhi/services/write_service.py`
- `src/pizhi/core/paths.py`
- `src/pizhi/core/config.py` when budget guard settings need config-backed defaults

## Testing Strategy

### Unit tests

- continue session creation and state transitions
- checkpoint creation and lookup
- orchestration state machine for start, apply, and resume
- checkpoint batch apply ordering and all-or-nothing behavior
- outline auto-splitting on budget overflow
- write budget overflow blocking behavior

### Integration tests

- `continue --execute` creates a session and first checkpoint
- `continue sessions` lists active sessions
- `checkpoints --session-id ...` lists session checkpoints
- `checkpoint apply --id ...` applies runs in deterministic order
- `continue resume --session-id ...` only works after checkpoint apply
- provider failure, normalize failure, budget failure, and apply failure correctly block the session
- prompt-only `continue` still works without provider execution

### Regression rule

Milestones 1-6 remain green. Orchestration must be additive and must not destabilize single-command provider execution.

## Acceptance Criteria

- `continue --execute` starts a persistent continue session
- provider-backed continue pauses every three chapters at explicit checkpoints
- outline and write checkpoints are separate and ordered
- checkpoint apply is batch, deterministic, and all-or-nothing
- session resume only proceeds from applied truth-source state
- users can inspect sessions and checkpoints through CLI commands
- budget overflow produces bounded, readable behavior
- existing prompt-only and milestone 6 single-command flows remain unchanged
