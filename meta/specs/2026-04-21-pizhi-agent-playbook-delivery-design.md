# Pizhi Design: Agent Playbook Delivery

**Date:** 2026-04-21
**Status:** Proposed

## Goal

Ship a versioned, repository-contained agent playbook for `Pizhi` so that a user can:

1. install the `pizhi` CLI through `uv` or Git-backed `uvx`
2. load the repository's `agents/pizhi/` directory into an external agent environment
3. have that agent drive the full `Pizhi` workflow exclusively through the `pizhi` CLI

The playbook is part of the project's public delivery surface, not an internal milestone artifact.

## Non-Goals

- No new CLI commands
- No changes to provider behavior
- No host-specific adapters for Codex, Claude Code, Opencode, or any other agent runtime
- No plugin marketplace metadata
- No auto-installer or bootstrap script for agent hosts
- No new product features beyond the playbook and its repository contracts

## Delivery Model

The playbook is shipped as a repository directory:

- `agents/pizhi/AGENTS.md`
- `agents/pizhi/resources/workflow.md`
- `agents/pizhi/resources/commands.md`
- `agents/pizhi/resources/failure-recovery.md`
- `agents/pizhi/resources/examples.md`

Expected usage:

1. The user installs the `pizhi` CLI
2. The user points their agent runtime at `agents/pizhi/`
3. The agent reads `AGENTS.md`
4. The agent uses the `pizhi` CLI as the only workflow surface

This design intentionally treats the playbook as a host-agnostic directory-level delivery artifact.

## Why `agents/pizhi/`

The playbook should live in a dedicated delivery directory rather than `meta/` or a generic docs subtree because:

- it is part of the product deliverable
- it should be versioned with the repository
- it should be easy for users to locate and hand to an agent runtime
- it should remain separate from user-facing docs and internal milestone records

The root entry file is `AGENTS.md` because many agent systems already recognize or preferentially inspect that filename.

## Directory Structure

```text
agents/
  pizhi/
    AGENTS.md
    resources/
      workflow.md
      commands.md
      failure-recovery.md
      examples.md
```

### `agents/pizhi/AGENTS.md`

The entry point for agents. It should:

- define the playbook's purpose
- state prerequisites
- tell the agent which resource files to read for which situations
- state the highest-value workflow constraints up front

It should stay concise and act as a dispatcher, not a full command manual.

### `agents/pizhi/resources/workflow.md`

The end-to-end workflow reference. It should cover:

- installation preconditions
- initialization
- day-to-day author workflow
- `write`
- `continue`
- `runs`
- `apply`
- `review`
- `compile`
- completion/hand-off flow

### `agents/pizhi/resources/commands.md`

Task-oriented command guidance. It should organize CLI usage by intent, not by mirroring `--help` output verbatim.

### `agents/pizhi/resources/failure-recovery.md`

The failure branch guide. It should cover at least:

- provider not configured
- failed run
- rejected `apply`
- interrupted `continue` / checkpoint flow
- Git/uv installation behavior before the stable tag is published

### `agents/pizhi/resources/examples.md`

Concrete examples of how an agent should sequence commands for common scenarios.

## Agent Behavior Contract

The playbook is not only a command reference. Its main value is constraining agent behavior.

It must explicitly encode these rules:

### Installation and Version Rules

- Prefer the pinned tag path after the stable tag exists
- Before the stable tag is published, use the unpinned Git URL path
- Do not assume a pinned Git tag exists before it has actually been released

### Workflow Rules

- Start from `pizhi status` before taking major action
- Treat provider-backed generation as a two-step flow:
  - `--execute` produces candidate output
  - `apply` mutates source-of-truth files
- Do not conflate generated output with applied state
- Treat `continue` as a checkpoint workflow:
  - inspect checkpoints
  - apply checkpoints explicitly
  - do not report completion merely because a session started
- Prefer review after writing and compile only when producing manuscript output

### Prohibited Actions

The playbook should explicitly tell agents not to:

- edit `.pizhi/` source-of-truth files directly to bypass the CLI
- `apply` failed runs
- claim `continue` completed before required checkpoints are applied
- assume a pinned tag path is valid before release
- change provider configuration unless the user asked for it

## Public vs Governance Consistency

The playbook and public repository docs must stay aligned with repository governance:

- public install docs can describe the pinned stable path
- if the release tag is not yet published, they must say that explicitly
- governance docs must not claim a tag already exists unless it has actually been created

This is especially important because the playbook will be consumed by agents that may follow documentation literally.

## Installation Model

The playbook should describe usage in two layers.

### Layer 1: Install the CLI

Support:

- local source workflows
- Git-backed `uvx`
- Git-backed `uv tool install`
- stable pinned tag usage when published

### Layer 2: Load the Playbook

Do not assume a host-specific format. Instead describe the playbook as a directory that should be loaded or registered with an agent runtime, with `AGENTS.md` as the entry point.

This keeps the delivery host-agnostic while still being directly useful.

## README Integration

The main repository `README.md` should gain a short pointer to the agent playbook delivery directory so users can discover it without searching the tree manually.

This pointer should be brief and should not duplicate the playbook contents.

## Validation Strategy

Validation should cover three areas.

### 1. Repository Structure Contracts

Assert that:

- `agents/pizhi/AGENTS.md` exists
- required resource files exist

### 2. Documentation Contracts

Assert that:

- `README.md` points to the agent playbook
- `AGENTS.md` contains the core workflow constraints
- failure recovery documentation contains the key failure scenarios

### 3. Full Regression

Run the repository's normal full suite:

```bash
python -m pytest tests/unit tests/integration -q --tb=short -rfE
```

## Implementation Scope

This milestone should touch only:

- `agents/pizhi/AGENTS.md`
- `agents/pizhi/resources/workflow.md`
- `agents/pizhi/resources/commands.md`
- `agents/pizhi/resources/failure-recovery.md`
- `agents/pizhi/resources/examples.md`
- `README.md`
- repository contract tests that validate the new delivery surface

## Completion Criteria

This work is complete when:

- the repository contains a versioned `agents/pizhi/` delivery directory
- `AGENTS.md` acts as a clear entry point for agents
- the resource docs cover workflow, command usage, recovery, and examples
- `README.md` points users to the playbook
- contract tests protect the new delivery surface
- the full test suite passes
