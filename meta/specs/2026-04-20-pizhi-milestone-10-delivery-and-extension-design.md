# Pizhi Milestone 10 Design: Delivery and Extension Closure

Date: 2026-04-20
Status: Proposed
Scope: Milestone 10

## 1. Goal

Milestone 10 closes the project as a usable v1 delivery while formalizing the first extension boundary for future agent-based growth.

The target outcome is:

- Pizhi exposes a minimal internal agent-extension contract for review and maintenance flows
- extension agents are registered declaratively and executed through controlled system-owned hooks
- review and maintenance reports can safely include extension-agent output without risking source-of-truth corruption
- user-facing documentation is complete enough for a new user to install, configure, run, recover, and maintain a project without relying on prior discussion context
- the architecture documentation reflects the implemented v1 extension boundary instead of leaving it as an open intention

This milestone is the project closure step for the planned ten-milestone roadmap.

## 2. Non-Goals

This milestone explicitly does not include:

- multi-agent orchestration across writing flows
- agent participation in `brainstorm`, `outline`, `write`, or `continue`
- arbitrary script/plugin execution
- new provider adapters or multi-provider support
- new AI review categories beyond the current review and maintenance extension surface
- external network-based agent delegation inside product flows

## 3. Primary Decisions

### 3.1 Agent extensibility is internal-first

Milestone 10 introduces extension points through internal registration and configuration only.

There is no dedicated `pizhi agent ...` CLI in v1. The goal is to stabilize extension boundaries before adding a public management surface.

### 3.2 Extension hooks are limited to low-risk diagnostic flows

The first supported hook families are:

- `review`
- `maintenance`

These hooks sit on diagnostic or post-processing paths rather than narrative-generation paths. This keeps the extension layer away from source-authoring responsibilities in v1.

### 3.3 Extension agents are additive, not authoritative

Extension agents do not replace built-in deterministic or AI review behavior.

They run after the built-in system path and append additional structured findings. The core system remains the only component that owns report shaping and any source-of-truth writes.

### 3.4 Delivery documentation is part of the product surface

Milestone 10 treats `README`, runbooks, failure-recovery guides, and command-help consistency as deliverable software artifacts rather than optional polish.

## 4. Agent Extension Model

Milestone 10 introduces a minimal extension model built around declaration, registration, and controlled execution.

Recommended core structures:

- `AgentSpec`
- `AgentRegistry`
- `AgentExecutionResult`

`AgentSpec` should describe:

- `agent_id`
- `kind`
- `description`
- `enabled`
- prompt template reference or inline prompt source
- supported targets, such as `chapter` or `project`

The first supported `kind` values are:

- `review`
- `maintenance`

The registry is loaded from project configuration and resolved at runtime by the main system. This keeps extension state visible, auditable, and deterministic.

## 5. Configuration Design

Milestone 10 adds an `agents:` section to `.pizhi/config.yaml`.

This section should be optional. Projects without configured agents must behave exactly as they do today.

The `agents:` section should support a list of extension entries whose shape can be validated strictly at load time. Invalid or unknown entries should fail configuration validation rather than silently disappearing.

Recommended behavior:

- omitted `agents:` means no extension agents are registered
- disabled agents stay in config but do not execute
- unknown `kind` values are rejected
- incomplete specs are rejected with readable validation messages

This milestone does not add a separate configuration command for agents. Configuration can remain file-based for v1 because the surface is aimed at advanced extension and internal growth, not first-run onboarding.

## 6. Execution Contract

Extension agents must execute through a system-owned contract rather than direct file access.

Each extension invocation should receive:

- a bounded context payload prepared by the main system
- a precise task target, such as one chapter or the full project
- a standard output schema for findings, summary, and optional recommendations

Each extension invocation must return structured data, not arbitrary prose blobs intended to be pasted directly into project files.

Recommended result shape:

- `status`
- `summary`
- `issues`
- `suggestions`
- optional `failure_reason`

This keeps extension output composable, testable, and safe to append into generated reports.

## 7. Hook Placement and Behavior

Milestone 10 supports two hook families.

### 7.1 Review hooks

Supported entry points:

- `review --execute --chapter`
- `review --execute --full`

Execution order:

1. built-in structural review completes
2. built-in AI review completes when requested
3. enabled `review` extension agents run serially
4. the final review document is assembled with isolated sections per extension agent

### 7.2 Maintenance hooks

Supported entry points:

- maintenance closure flows
- archive-oriented review/maintenance flows
- candidate-audit style diagnostic flows already owned by the maintenance layer

Execution order:

1. built-in deterministic maintenance logic completes
2. enabled `maintenance` extension agents run serially
3. extension output is appended to the corresponding report artifact

### 7.3 Failure isolation

An extension-agent failure must not invalidate or corrupt the main flow.

Required behavior:

- built-in review or maintenance output still succeeds when possible
- failing extension agents are recorded as failed
- failure information is surfaced in the generated report or run record
- source-of-truth files are never left half-written because an extension agent failed

## 8. Report Integration

Milestone 10 should integrate extension output through explicit report sections owned by the main system.

For chapter notes and project-level reports:

- built-in sections remain canonical
- each extension agent gets a dedicated appended section
- section labels include the agent identifier
- duplicate or malformed extension payloads are rejected or normalized before rendering

This follows the same principle already used elsewhere in Pizhi: generated artifacts can be merged and maintained only when the system owns the outer structure.

## 9. Delivery Documentation

Milestone 10 should leave the repository self-sufficient for first-time use.

Required documentation closure:

- `README` with project purpose, capability summary, and shortest-start path
- user runbook covering:
  - initialization
  - provider configuration
  - `brainstorm`
  - `outline`
  - `write`
  - `apply`
  - `continue`
  - `review`
  - `compile`
  - maintenance and archive expectations
- failure-recovery guidance covering:
  - provider execution failure
  - normalization or apply failure
  - `continue resume --session-id`
  - review and maintenance retry guidance
- command-help consistency for the major CLI paths

The documentation target is not "many docs". The target is that a new user can independently run the product from project init to manuscript compilation and understand how to recover from the most likely failures.

## 10. Architecture Closure

Milestone 10 should update architecture documentation so the extension boundary is no longer described as future intent.

The architecture should clearly state:

- v1 includes an internal extension-agent contract
- supported hook families are `review` and `maintenance`
- extension agents are additive and non-authoritative
- source-of-truth writes remain owned by the core system

This closes the remaining ambiguity around how extensibility exists in the v1 product without overcommitting to a future plugin system.

## 11. Expected Files

Expected modified files will likely include:

- `src/pizhi/core/config.py`
- `src/pizhi/services/ai_review_service.py`
- `src/pizhi/services/review_documents.py`
- maintenance-related orchestration and report services
- `src/pizhi/cli.py` only if help text or surfaced flow docs need alignment
- `docs/architecture/ARCHITECTURE.md`
- `README.md`
- new or expanded runbook and recovery docs under `docs/`

Expected new code-focused files may include:

- an agent-domain module
- an agent-registry module
- an extension-execution module

The exact filenames should follow existing codebase boundaries during implementation rather than forcing a speculative layout here.

## 12. Testing Strategy

### 12.1 Unit tests

- configuration parsing and validation for `agents:`
- registry behavior for enabled and disabled agents
- hook dispatch for `review` and `maintenance`
- failure isolation when an extension agent returns an invalid payload or raises an execution error
- report rendering with appended extension sections

### 12.2 Integration tests

- project with no configured agents behaves identically to current behavior
- enabled review extension appends its section to chapter or full-review output
- enabled maintenance extension appends its section to maintenance-style output
- failing extension is reported without breaking the main review or maintenance result

### 12.3 Documentation and contract verification

- command help and documented examples stay aligned
- a smoke path based on the published runbook remains executable
- documentation references use real command names, real file paths, and existing workflow steps

### 12.4 Full regression

Milestone 10 should continue using the quiet full-suite command for normal regression:

`python -m pytest tests/unit tests/integration -q --tb=short -rfE`

## 13. Expected Outcome

After milestone 10:

- Pizhi is a deliverable v1 product rather than a feature-complete but discussion-dependent tool
- the project has a stable, documented extension boundary for future review and maintenance agents
- the repository documentation matches the real product behavior closely enough for independent use
- the planned ten-milestone roadmap is complete without opening a new core capability track
