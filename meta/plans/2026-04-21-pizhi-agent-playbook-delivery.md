# Pizhi Agent Playbook Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a versioned, repository-delivered `agents/pizhi/` playbook so external agents can load it and drive the full `Pizhi` workflow through the `pizhi` CLI.

**Architecture:** Treat the playbook as a delivery artifact rather than an internal meta document. Add a thin `agents/pizhi/AGENTS.md` entrypoint that dispatches to focused resource docs, then lock the delivery surface with repository/documentation contract tests and a short README pointer.

**Tech Stack:** Markdown documentation, repository contract tests with pytest, existing CLI workflow semantics, Git versioning, agent-oriented playbook design

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\agent-playbook-delivery`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -q --tb=short -rfE`
  - Observed while writing this plan: `319 passed in 92.97s`

## File Map

- `agents/pizhi/AGENTS.md`: entrypoint for external agents; declares prerequisites, loading order, core workflow rules, and prohibited actions
- `agents/pizhi/resources/workflow.md`: full author workflow from install through compile, including execute/apply and continue/checkpoint semantics
- `agents/pizhi/resources/commands.md`: task-oriented CLI reference grouped by agent intent rather than raw help output
- `agents/pizhi/resources/failure-recovery.md`: failure branches for provider setup, failed runs, rejected apply, checkpoint interruption, and pre-tag pinned Git install behavior
- `agents/pizhi/resources/examples.md`: concrete agent command sequences for common scenarios
- `README.md`: short pointer to the `agents/pizhi/` delivery artifact
- `tests/integration/test_docs_contract.py`: public-doc contract checks for the README pointer and key agent-playbook guidance markers
- `tests/integration/test_repository_layout_contract.py`: repository-shape contract checks for `agents/pizhi/` and required playbook resources
- `meta/specs/2026-04-21-pizhi-agent-playbook-delivery-design.md`: approved design doc; leave unchanged
- `meta/plans/2026-04-21-pizhi-agent-playbook-delivery.md`: this plan; update observed verification notes if execution results differ

### Task 1: Add Agent Playbook Delivery Contracts

**Files:**
- Modify: `tests/integration/test_repository_layout_contract.py`
- Modify: `tests/integration/test_docs_contract.py`

- [ ] **Step 1: Write the failing repository and docs contract tests**

```python
def test_agent_playbook_delivery_exists(project_root):
    expected = [
        "agents/pizhi/AGENTS.md",
        "agents/pizhi/resources/workflow.md",
        "agents/pizhi/resources/commands.md",
        "agents/pizhi/resources/failure-recovery.md",
        "agents/pizhi/resources/examples.md",
    ]

    for relative in expected:
        assert (project_root / relative).exists(), relative


def test_readme_points_to_agent_playbook(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    assert "agents/pizhi/" in readme
    assert "AGENTS.md" in readme


def test_agent_playbook_contract_markers(project_root):
    agents_md = (project_root / "agents" / "pizhi" / "AGENTS.md").read_text(encoding="utf-8")
    recovery = (project_root / "agents" / "pizhi" / "resources" / "failure-recovery.md").read_text(encoding="utf-8")

    assert "pizhi status" in agents_md
    assert "--execute" in agents_md
    assert "apply" in agents_md
    assert "checkpoints" in agents_md
    assert "Do not edit `.pizhi/`" in agents_md
    assert "provider not configured" in recovery
    assert "failed run" in recovery
    assert "checkpoint" in recovery
    assert "v0.1.0" in recovery
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- failures because `agents/pizhi/` does not exist yet
- failure because `README.md` does not yet point to the playbook

- [ ] **Step 3: Keep the contract scope tight**

Only assert:

- the delivery directory exists
- the required resource files exist
- the README pointer exists
- the playbook includes the highest-value workflow and recovery constraints

Do not assert host-specific integration commands or raw CLI help output.

- [ ] **Step 4: Re-run the targeted tests**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- selected tests still fail because the playbook files and README pointer do not exist yet

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py
git commit -m "test: add agent playbook delivery contracts"
```

### Task 2: Add `agents/pizhi/` Entry Point And Core Workflow Docs

**Files:**
- Create: `agents/pizhi/AGENTS.md`
- Create: `agents/pizhi/resources/workflow.md`
- Create: `agents/pizhi/resources/commands.md`
- Modify: `tests/integration/test_docs_contract.py`

- [ ] **Step 1: Write the entrypoint and workflow resources**

`agents/pizhi/AGENTS.md` should stay concise and include:

- what the playbook is for
- prerequisites
- which resource files to read
- core rules:
  - start with `pizhi status`
  - `--execute` generates candidates
  - `apply` mutates source-of-truth
  - `continue` is checkpoint-based
  - do not bypass the CLI by editing `.pizhi/`

`workflow.md` should cover the full author flow from install through compile.

`commands.md` should group commands by agent task, e.g. inspect, generate, apply, continue, review, compile.

- [ ] **Step 2: Run the targeted docs/repository tests**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- some tests still fail because failure-recovery/examples and README pointer are not in place yet

- [ ] **Step 3: Keep the docs host-agnostic**

Do not write host-specific instructions for Codex, Claude Code, or Opencode.

Do write:

- install the CLI first
- then load `agents/pizhi/`
- then start at `AGENTS.md`

- [ ] **Step 4: Re-run the targeted tests after the minimal docs land**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- reduced failure set or full pass depending on remaining README/recovery gaps

- [ ] **Step 5: Commit**

```bash
git add agents/pizhi/AGENTS.md agents/pizhi/resources/workflow.md agents/pizhi/resources/commands.md tests/integration/test_docs_contract.py
git commit -m "docs: add agent playbook entrypoint"
```

### Task 3: Add Failure Recovery, Examples, And README Pointer

**Files:**
- Create: `agents/pizhi/resources/failure-recovery.md`
- Create: `agents/pizhi/resources/examples.md`
- Modify: `README.md`
- Modify: `tests/integration/test_docs_contract.py`
- Modify: `tests/integration/test_repository_layout_contract.py`

- [ ] **Step 1: Add the recovery and examples docs**

`failure-recovery.md` must cover:

- provider not configured
- failed run
- rejected `apply`
- interrupted `continue` / checkpoint flow
- pre-tag `@v0.1.0` behavior

`examples.md` should include a few realistic agent sequences, e.g.:

- fresh project setup
- single chapter write + apply + review
- continue session with checkpoints
- stable install path after tag release

- [ ] **Step 2: Add the README pointer**

Keep the README change short:

- mention that `agents/pizhi/` is a delivery artifact for external agents
- point users to `agents/pizhi/AGENTS.md`
- avoid duplicating the playbook contents in the README

- [ ] **Step 3: Run the focused contract tests**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- selected tests `PASSED`

- [ ] **Step 4: Run CLI/help contract coverage**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py tests/integration/test_cli_help_contract.py -q --tb=short -rfE`

Expected:
- all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add agents/pizhi/resources/failure-recovery.md agents/pizhi/resources/examples.md README.md tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py
git commit -m "docs: deliver agent playbook resources"
```

### Task 4: Verify Full Regression And Record Plan Notes

**Files:**
- Modify: `meta/plans/2026-04-21-pizhi-agent-playbook-delivery.md`

- [ ] **Step 1: Run the full regression suite**

Run:
`python -m pytest tests/unit tests/integration -q --tb=short -rfE`

Expected:
- full suite `PASSED`

- [ ] **Step 2: Record the observed verification result in this plan**

If the final observed result differs from:

- `319 passed in 92.97s`

record the observed result in a separate execution note without rewriting the baseline instruction.

- [ ] **Step 3: Add a short execution note about the delivery surface**

Record that:

- `agents/pizhi/` is now present as a repository-shipped delivery directory
- `README.md` points to it
- the playbook remains host-agnostic and CLI-driven

- [ ] **Step 4: Commit**

```bash
git add meta/plans/2026-04-21-pizhi-agent-playbook-delivery.md
git commit -m "docs: record agent playbook delivery verification"
```

## Notes

- Do not introduce host-specific installation instructions into the playbook.
- Keep `AGENTS.md` short and use `resources/` for detail.
- Avoid copying full CLI help text into the playbook.
- The playbook should constrain agent behavior, not merely list commands.

## Execution Notes

- Final observed regression result:
  - `python -m pytest tests/unit tests/integration -q --tb=short -rfE`
  - `323 passed in 90.65s (0:01:30)`
- Additional verification:
  - `python -m pizhi --help`
  - observed: CLI help rendered successfully
- Delivery surface now present:
  - `agents/pizhi/` is a repository-shipped delivery directory
  - `README.md` points external agents to `agents/pizhi/AGENTS.md`
  - the playbook remains host-agnostic and CLI-driven
