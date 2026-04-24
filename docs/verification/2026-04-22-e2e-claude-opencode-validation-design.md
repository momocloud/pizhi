# Pizhi E2E Validation Design

Date: 2026-04-22
Status: proposed

## Purpose

This document defines a real-host end-to-end validation run for the shipped delivery stack:

- `Claude Code` as the real host entry
- `agents/pizhi/` as the versioned host-side playbook
- `Pizhi` as the orchestrator and source-of-truth manager
- `opencode` as the execution backend

The goal is not to prove literary quality. The goal is to prove that the delivered stack can sustain a real long-form workflow under realistic load.

## Scope

The validation project will be a new urban-fantasy novel generated in a temporary directory outside the repository.

The validation is staged:

1. `Stage 1: 3-chapter smoke`
2. `Stage 2: 10-chapter endurance`
3. `Stage 3: 30-chapter full run`

Each stage reuses the same architecture and operational rules. The only change is the workload size.

## Validation Stack

The stack is intentionally fixed:

- `Claude Code` loads and follows `agents/pizhi/AGENTS.md`
- `Claude Code` drives `pizhi` CLI commands
- `Pizhi` manages project state, sessions, checkpoints, runs, review, and compile
- `opencode` executes backend-backed `--execute` steps

This validation does not treat `Claude Code` as a backend. It remains the host. The backend remains `opencode`.

## Project Placement

### Temporary project root

The generated novel project lives outside the repository in a temporary validation directory, for example:

`C:\Users\kywin\ownProject\noval\tmp\pizhi-e2e-claude-opencode-<timestamp>\`

This directory is not tracked in Git.

### Versioned validation archive

The repository stores only validation procedure and result documents.

Validation reports live in:

- `docs/verification/`

Expected outputs include:

- `docs/verification/2026-04-22-e2e-stage-1-smoke.md`
- `docs/verification/2026-04-22-e2e-stage-2-endurance.md`
- `docs/verification/2026-04-22-e2e-stage-3-full-run.md`

An additional summary or index document may be added if useful.

## Stage Goals

### Stage 1: 3-chapter smoke

The smoke stage verifies that the real delivery stack can complete the minimum meaningful loop:

- initialize a project
- configure the agent backend
- generate a working story direction
- run checkpointed `continue --execute`
- auto-apply generated runs and checkpoints
- complete at least 3 chapters
- run `review --full`
- run `compile`

This stage is primarily about basic correctness of orchestration, apply flow, checkpoint flow, and host/backend integration.

### Stage 2: 10-chapter endurance

The endurance stage verifies that the same system remains stable when the session/checkpoint cycle repeats multiple times.

This stage focuses on:

- stable continue-session progression
- repeated checkpoint generation and application
- continued write/review/maintenance behavior
- continued compile viability after more accumulated state

### Stage 3: 30-chapter full run

The full-run stage verifies that the stack can survive a medium-length novel workload under realistic sustained use.

This stage focuses on:

- long-running session and run stability
- continued source-of-truth consistency
- practical review/report usefulness at scale
- compile output remaining available after a significantly larger chapter set

## Execution Rules

### Automatic application

This validation uses automatic apply progression.

The automation is allowed to:

- apply successful ordinary runs with `apply --run-id`
- apply checkpoints with `checkpoint apply --id`
- continue advancing sessions with `continue run --execute` and `continue resume --session-id`

The automation is not allowed to:

- silently change prompts to rescue a run
- silently change configuration mid-stage without recording it
- patch project files to hide failures
- reclassify failures as success

The purpose is to validate the system, not the operator's ability to improvise hidden fixes.

### Fixed host chain

Every stage uses the same real chain:

`Claude Code -> agents/pizhi/ -> Pizhi CLI -> opencode backend`

No stage is allowed to bypass that chain for convenience.

## Pass/Stop Policy

The user selected a wide stop threshold. Therefore this validation behaves like a soak test rather than a strict gate.

### Stage completion

- `Stage 1` passes if the 3-chapter loop basically completes and both `review --full` and `compile` complete.
- `Stage 2` passes if the workflow reaches 10 chapters and completes stage-end review and compile.
- `Stage 3` passes if the workflow basically reaches 30 chapters and completes the final validation closure.

### Failure handling

Problems are still classified, but they do not automatically end the stage unless the system becomes impossible to continue.

Problem classes:

- `Blocking`
  - state machine failure
  - run or checkpoint apply failure that prevents meaningful continuation
  - compile unavailable
  - session cannot recover
- `Major`
  - workflow continues, but review, maintenance, or session behavior is clearly wrong
- `Minor`
  - formatting, noisy warnings, or non-blocking usability issues

The run should continue when possible, but every issue must be recorded in the stage report.

## Reporting Model

Each stage produces two layers of record.

### Main stage report

Each stage report includes:

- environment and host/backend configuration
- actual chapter span achieved
- command flow summary
- warnings and failures summary
- `review --full` outcome
- `compile` outcome
- decision to proceed or stop

### Detailed run index

Each stage also records traceability data, including key:

- `session_id`
- `checkpoint_id`
- `run_id`
- output directories
- failure points
- important artifact paths

This gives both a management-friendly summary and a debug-friendly appendix.

## Non-goals

This validation explicitly does not do the following:

- store the generated novel project in the repository
- silently modify the playbook or prompt contracts without recording the change
- turn `Claude Code` host automation into a productized runner in this step
- expand this effort into a benchmarking platform
- guarantee literary quality as the primary evaluation metric

## Expected Outcome

If all three stages complete, the result should be a high-confidence statement that the shipped delivery stack is viable for sustained real-host use.

If any stage exposes failures, the result should still be useful:

- a reproducible temporary project
- a versioned report
- concrete artifact paths
- a clear problem classification for follow-up work
