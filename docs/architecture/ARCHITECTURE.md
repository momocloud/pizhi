# Pizhi Architecture

Date: 2026-04-20
Status: v1 implemented

## Purpose

Pizhi is a CLI for long-form fiction workflows that keeps project state on disk, keeps provider execution auditable, and reserves source-of-truth writes for deterministic application steps.

The product surface now includes:

- deterministic project initialization and file layout
- provider-backed generation with explicit run recording
- explicit `apply --run-id` for source-of-truth mutation
- checkpointed `continue` execution and resume support
- structural review, optional AI review, and built-in maintenance
- manuscript compilation by volume, chapter, or chapter range
- internal extension hooks for review and maintenance only

## System Boundaries

### Core state

The project root holds two distinct surfaces:

- `.pizhi/`: system-owned working state, configuration, runs, review artifacts, sessions, and checkpoints
- `manuscript/`: user-facing compiled output

This separation keeps mutable working data away from published manuscript slices.

### Deterministic vs provider-backed work

Pizhi uses two execution modes:

- deterministic commands that update project files directly
- provider-backed commands that first write auditable run artifacts under `.pizhi/cache/runs/<run_id>/`

Provider-backed generation is never authoritative by itself. Source-of-truth writes happen only when the user explicitly applies a successful run or when a built-in deterministic closure step owns the update path.

## Command Architecture

### Planning and drafting

- `init` creates the baseline file tree and config
- `brainstorm`, `outline expand`, and `write` support prompt-only and `--execute` flows
- `continue run` supports prompt-only operation or provider-backed execution with persisted sessions and checkpoints

### Review and compilation

- `review --chapter` and `review --full` always run built-in structural review
- `review --execute` layers provider-backed AI review on top of the built-in review path
- `review --full` also runs deterministic maintenance and writes a full review report
- `compile` renders manuscript output by volume, chapter, or chapter range

### Auditable provider flow

The canonical provider-backed pattern is:

1. execute a command such as `brainstorm --execute`, `write --execute`, or `continue run --execute`
2. inspect recorded runs with `runs`
3. apply the chosen result with `apply --run-id <run_id>`

This keeps prompt execution, normalization, and source mutation separable and inspectable.

## Storage Layout

Key directories and files:

- `.pizhi/config.yaml`: project configuration plus optional provider and extension-agent settings
- `.pizhi/global/`: global story state
- `.pizhi/chapters/chNNN/`: per-chapter outlines, text, snapshots, and notes
- `.pizhi/cache/runs/<run_id>/`: prompt, raw payload, normalized output, and manifest for provider-backed runs
- `.pizhi/cache/review_full.md`: full-project review artifact
- `.pizhi/continue_sessions/` and `.pizhi/checkpoints/`: persisted continue execution state
- `manuscript/`: compiled reading-facing outputs

The directory structure is part of the architecture because the filesystem is the durable state boundary.

## Review and Maintenance Pipeline

### Built-in review path

`review` always starts with structural checks. For chapter review, the output lands in `notes.md`. For full review, the report is written to `.pizhi/cache/review_full.md`.

### AI review path

`review --execute` adds provider-backed AI review after structural review completes. If AI review fails, the built-in structural report remains available and the failure is rendered into the report instead of replacing it.

### Maintenance path

Maintenance is system-owned and deterministic. In v1 it runs through built-in flows such as full review and apply-driven closure rather than a public standalone maintenance CLI.

## v1 Extension Boundary

Pizhi now exposes a minimal internal extension-agent contract.

### Supported hook families

Only these hook families are supported in v1:

- `review`
- `maintenance`

There are no extension hooks for `brainstorm`, `outline`, `write`, `continue`, or `compile`.

### Registration

Extension agents are declared in the optional `agents:` section of `.pizhi/config.yaml`. Each spec is validated at config load time and then resolved through the runtime registry.

### Execution contract

The core system prepares bounded context for each invocation, executes enabled agents serially, and normalizes results into system-owned report sections.

Extension agents are:

- additive
- non-authoritative
- failure-isolated

They can append findings to notes or reports, but they do not own chapter files, global files, or other source-of-truth mutations.

### Failure model

If an extension setup or runtime failure occurs:

- the built-in review or maintenance path still completes when possible
- the failure is rendered as an isolated section in the report
- the core system remains responsible for all canonical document structure

This boundary is intentionally narrow. It supports future diagnostic growth without committing v1 to a general plugin system.

## Product Closure Notes

The repository is intended to be usable without prior milestone context. The delivery surface therefore includes:

- `README.md` as the shortest entry point
- `docs/guides/getting-started.md` as the canonical runbook
- `docs/guides/recovery.md` as failure-handling guidance
- this architecture document as the canonical system overview
