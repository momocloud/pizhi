# Pizhi Milestone 11 Design: Agent Execution Backend

Date: 2026-04-21
Status: Proposed
Scope: Milestone 11

## 1. Goal

Milestone 11 upgrades Pizhi from a provider-backed execution CLI into a backend-pluggable execution CLI.

The first new backend is an `agent` backend implemented through `opencode`.

This milestone exists because some coding plans can only be executed through an agent runtime rather than a direct LLM provider API. Pizhi must support that execution model without losing its existing run recording, explicit apply, checkpoint, and deterministic source-of-truth guarantees.

The target outcome is:

- Pizhi keeps its existing deterministic core and orchestration semantics
- execution becomes a backend abstraction rather than a provider-only abstraction
- `opencode` becomes the first supported `agent` backend
- Pizhi generates a per-run temporary task package and temporary skill for `opencode`
- `opencode` produces candidate output into a designated file inside the run directory
- Pizhi reads that output and continues using the existing `runs`, `apply`, `continue`, and `review` flows
- the recommended user-facing entry remains `Claude Code + repository-shipped skill`, while `Claude Code` itself does not become a Pizhi backend

## 2. Non-Goals

This milestone explicitly does not include:

- removing or replacing the current provider backend
- supporting multiple agent backends in the first implementation
- making `Claude Code` a backend inside Pizhi
- letting `opencode` write project source-of-truth files directly
- handing complete continue sessions or complete project workflows to `opencode`
- automatic backend auto-detection
- debate-style or multi-agent orchestration
- changing deterministic commands such as `status`, `apply`, `checkpoint`, or `compile` into backend-driven operations

## 3. High-Level Architecture

Milestone 11 clarifies Pizhi into three layers:

1. Host entry layer
   - external user-facing agent host such as `Claude Code`
   - loads a repository-shipped skill and uses it to drive the Pizhi CLI
   - does not become part of Pizhi's backend contract

2. Pizhi orchestration layer
   - command parsing
   - prompt and request assembly
   - run storage
   - explicit apply
   - continue session and checkpoint orchestration
   - review orchestration
   - deterministic source-of-truth writes

3. Execution backend layer
   - provider backend
   - agent backend
   - both return candidate content into the same run-store-driven lifecycle

The architectural rule is:

- Pizhi orchestrates workflows
- execution backends execute individual generation or review steps
- external hosts drive the CLI, but do not replace Pizhi's state model

## 4. Backend Model

Milestone 11 replaces the current provider-only execution concept with a generic execution backend contract.

Proposed backend types:

- `provider`
- `agent`

Both backend types must support the same high-level lifecycle:

1. receive a standard execution request from Pizhi
2. execute one candidate-producing step
3. return raw execution artifacts plus normalized candidate text
4. let Pizhi write the run record
5. leave source-of-truth mutation to explicit `apply` or checkpoint-apply flows

The current provider execution path remains valid, but is refactored to become one backend implementation instead of the only execution path.

## 5. First Agent Backend: `opencode`

The first `agent` backend implementation is `opencode`.

Milestone 11 intentionally supports only one agent runtime in the first release because agent CLIs differ in task packaging, invocation style, and output capture. The backend abstraction must stabilize before adding more hosts.

The first implementation therefore is:

- backend kind: `agent`
- backend implementation: `opencode`

Future backends such as `claudecode` or other agents may be added later through the same abstraction, but they are out of scope for this milestone.

## 6. Command Coverage

Milestone 11 supports agent backend execution only for commands that already have execute-style candidate generation semantics.

In-scope commands:

- `pizhi brainstorm --execute`
- `pizhi outline expand --execute`
- `pizhi write --execute`
- `pizhi review --execute`
- `pizhi continue run --execute`
- `pizhi continue resume --session-id <id>`

Out-of-scope commands:

- `pizhi status`
- `pizhi runs`
- `pizhi apply`
- `pizhi checkpoint`
- `pizhi checkpoints`
- `pizhi compile`

These remain deterministic orchestration and reporting commands.

## 7. Workflow Responsibility Split

Milestone 11 preserves the current separation between workflow orchestration and step execution.

Rules:

- Pizhi remains the orchestrator for single-run, review, and continue-session workflows
- the backend executes only one step at a time
- `continue` remains a Pizhi-managed session and checkpoint state machine
- `opencode` is not allowed to absorb the entire multi-step workflow into one opaque agent task

This means:

- `brainstorm --execute` delegates one candidate-generation step to the backend
- `write --execute` delegates one chapter-generation step to the backend
- `review --execute` delegates one AI review generation step to the backend
- `continue --execute` still creates and manages checkpoints, but each outline/write step inside that session may be executed through the backend

The guiding rule is:

- backends execute steps
- Pizhi executes workflows

## 8. `opencode` File-Bridge Contract

Pizhi will not stream prompts directly into `opencode` standard input as the primary contract.

Instead, each run will include an agent task package inside the run directory.

Target run layout additions:

- `.pizhi/cache/runs/<run_id>/agent_request.json`
- `.pizhi/cache/runs/<run_id>/agent_task.md`
- `.pizhi/cache/runs/<run_id>/agent_skill/AGENTS.md`
- `.pizhi/cache/runs/<run_id>/agent_skill/resources/...`
- `.pizhi/cache/runs/<run_id>/agent_output.md`
- `.pizhi/cache/runs/<run_id>/agent_stdout.txt`
- `.pizhi/cache/runs/<run_id>/agent_stderr.txt`

Execution lifecycle:

1. Pizhi assembles the standard execution request
2. Pizhi writes an `agent_request.json` manifest
3. Pizhi renders a human-readable `agent_task.md`
4. Pizhi generates a temporary one-run skill under `agent_skill/`
5. Pizhi invokes `opencode` CLI against that task package
6. `opencode` writes the candidate response to `agent_output.md`
7. Pizhi reads `agent_output.md`
8. Pizhi writes the normal run-store artifacts and status

Important contract rules:

- `agent_output.md` is the authoritative output handoff file
- `stdout` and `stderr` are audit logs only
- the temporary skill must explicitly forbid direct source-of-truth mutation
- the temporary skill must scope the agent to the single requested step

## 9. Run Store Integration

Milestone 11 keeps the existing run store as the canonical audit surface.

The run store still owns:

- `prompt.md`
- `raw.json` or equivalent raw metadata artifact
- `normalized.md`
- `manifest.json`
- `error.txt`

For the `agent` backend, the raw execution record should additionally preserve:

- backend kind
- backend implementation name
- agent task file path
- agent output file path
- captured stdout/stderr paths

`normalized.md` remains the standardized candidate content consumed by apply and checkpoint flows.

This is critical because downstream logic such as `apply --run-id`, checkpoint apply, and review document writers should not care whether the candidate came from a provider backend or an agent backend.

## 10. Configuration Model

Milestone 11 generalizes execution configuration from a provider-only shape into a backend-aware shape.

The configuration must support:

- backend kind selection
- backend-specific settings
- existing model route settings where applicable

Conceptually:

- provider-backed projects continue to store provider/model configuration
- agent-backed projects store agent backend configuration

The first agent configuration must support at least:

- `agent_backend: opencode`
- `agent_command`
- `agent_args`
- any required non-interactive invocation flags

Configuration naming can evolve in implementation, but the milestone goal is architectural clarity:

- execution backend configuration is no longer provider-only configuration

## 11. Failure Handling

Agent backend failures must follow the same safety bar as provider failures.

If agent execution fails:

- the run directory must still be written
- status must be marked failed
- stdout and stderr must be preserved when available
- source-of-truth files must remain untouched

If the agent output file is missing, empty, or malformed:

- the run must be treated as failed or normalization-failed
- the failure must be explicit in the manifest and error file
- no implicit fallback apply is allowed

For `continue` session execution:

- failed step execution must not corrupt session or checkpoint bookkeeping
- Pizhi must keep the session resumable after fixing the backend issue

## 12. Documentation Model

Milestone 11 also clarifies the public integration story.

Recommended user-facing stack:

- `Claude Code` as the interactive host
- repository-shipped skill as the playbook
- `pizhi` CLI as the orchestrator
- `opencode` as the first agent execution backend

This distinction must be reflected in:

- `README.md`
- architecture documentation
- getting-started documentation
- the repository-shipped agent playbook

The documentation must not blur these roles together. In particular:

- `Claude Code` is not a Pizhi backend
- `opencode` is not the project state manager
- Pizhi remains the authoritative workflow and state boundary

## 13. Proposed Module Split

Suggested module changes:

- `src/pizhi/services/execution.py`
  - unified execution entry point
- `src/pizhi/backends/base.py`
  - backend request and response contract
- `src/pizhi/backends/provider_backend.py`
  - wraps existing provider execution path
- `src/pizhi/backends/agent_backend.py`
  - generic agent backend support
- `src/pizhi/backends/opencode_backend.py`
  - first concrete agent backend
- `src/pizhi/services/agent_task_package.py`
  - render `agent_request.json`, `agent_task.md`, and temporary skill package
- `src/pizhi/services/run_store.py`
  - extended metadata support for agent-backed runs

Command modules should stay orchestration-only.

## 14. Testing Strategy

Milestone 11 should prioritize contract tests over end-to-end agent realism.

Required coverage:

- backend selection tests
- provider backend regression tests
- agent task package rendering tests
- opencode invocation command construction tests
- run store metadata tests for agent-backed runs
- missing output / empty output / malformed output failure tests
- continue-session failure and resume behavior tests
- documentation contract tests for the clarified `Claude Code -> Pizhi -> opencode` stack

The first implementation can use stubs or fake agent commands in tests rather than requiring a real `opencode` installation in CI.

## 15. Milestone Outcome

Milestone 11 is successful when:

- Pizhi supports backend-pluggable execution
- current provider-backed flows still work
- agent-backed execution works through `opencode`
- `runs`, `apply`, `continue`, and `review` preserve their existing semantics
- public documentation clearly explains the host/orchestrator/backend split

At that point, Pizhi will no longer be limited to provider APIs as its only execution path, while still preserving the deterministic core that gives the project its value.
