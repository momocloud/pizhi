# Pizhi Milestone 11 Agent Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backend-pluggable execution layer to Pizhi, keep provider-backed execution working, and introduce an `opencode` agent backend that executes one step at a time through a per-run task package.

**Architecture:** Generalize the current provider-only execution path into a unified execution service with backend adapters. Preserve the existing run store, `apply`, `continue`, and `review` semantics, then add an `opencode` backend that communicates through generated task files, a temporary one-run skill, and a designated output file inside each run directory.

**Tech Stack:** Python 3.11+, argparse CLI, dataclasses, PyYAML config, subprocess-based agent invocation, markdown task packaging, pytest unit/integration tests, existing Pizhi run/checkpoint architecture

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\milestone-11-agent-backend`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -q --tb=short -rfE`
  - Observed while writing this plan: `323 passed in 93.28s (0:01:33)`

## File Map

- `src/pizhi/core/config.py`: generalize execution config from provider-only shape into backend-aware provider/agent sections while preserving backward compatibility for existing `provider:` configs
- `src/pizhi/cli.py`: add the new agent/backend configuration entrypoint without breaking existing command help or legacy flows
- `src/pizhi/commands/provider_cmd.py`: keep provider configuration behavior working against the new config shape or reduce it to a compatibility shim
- `src/pizhi/commands/agent_cmd.py`: create agent backend configuration command handling for `opencode`
- `src/pizhi/services/execution.py`: define the unified execution entrypoint used by execute-capable commands and continue/review services
- `src/pizhi/backends/base.py`: backend request/response dataclasses and backend protocol shared by provider and agent backends
- `src/pizhi/backends/provider_backend.py`: wrap existing provider behavior under the new backend contract
- `src/pizhi/backends/agent_backend.py`: shared agent-backend execution helpers such as subprocess capture and output-file normalization
- `src/pizhi/backends/opencode_backend.py`: first concrete agent backend implementation
- `src/pizhi/services/agent_task_package.py`: render `agent_request.json`, `agent_task.md`, and the temporary one-run skill package
- `src/pizhi/services/provider_execution.py`: convert to compatibility wrapper or retire call sites in favor of `services/execution.py`
- `src/pizhi/services/continue_execution.py`: switch continue checkpoint generation from provider-only execution to the unified execution service
- `src/pizhi/services/ai_review_service.py`: route AI review execution through the unified execution service
- `src/pizhi/commands/brainstorm_cmd.py`: route `--execute` through the unified execution service
- `src/pizhi/commands/outline_cmd.py`: route `--execute` through the unified execution service
- `src/pizhi/commands/write_cmd.py`: route `--execute` through the unified execution service
- `src/pizhi/services/run_store.py`: extend run manifest metadata and path bookkeeping for agent-backed artifacts
- `tests/unit/test_config.py`: backend-aware config round trips and backward compatibility
- `tests/integration/test_provider_configure_command.py`: preserve provider configuration behavior while the config model changes
- `tests/unit/test_provider_execution.py`: adapt existing provider execution tests to the unified execution service or compatibility wrapper
- `tests/unit/test_execution.py`: add unified execution backend-selection tests
- `tests/unit/test_agent_task_package.py`: add file-bridge rendering tests for task files and temporary skill content
- `tests/unit/test_opencode_backend.py`: add subprocess invocation and output-handoff tests for `opencode`
- `tests/unit/test_continue_execution.py`: keep continue failure/resume semantics intact under the new execution abstraction
- `tests/integration/test_provider_execution_commands.py`: preserve provider-backed command behavior under the unified backend entrypoint
- `tests/integration/test_review_command.py`: preserve review execute behavior and AI review wiring under the new execution abstraction
- `tests/integration/test_cli_help_contract.py`: lock any new CLI help surface
- `tests/integration/test_docs_contract.py`: verify docs mention the clarified `Claude Code -> Pizhi -> opencode` stack
- `README.md`: explain backend-pluggable execution and clarify host/orchestrator/backend roles
- `docs/architecture/ARCHITECTURE.md`: reflect backend-pluggable execution instead of provider-only framing
- `docs/guides/getting-started.md`: document agent backend configuration and expected `opencode` setup
- `agents/pizhi/AGENTS.md`: clarify that external hosts drive the CLI, while `opencode` can serve as an execution backend
- `agents/pizhi/resources/workflow.md`: describe how `--execute` behaves when the project is configured for an agent backend
- `meta/specs/2026-04-21-pizhi-milestone-11-agent-backend-design.md`: approved design doc; leave unchanged
- `meta/plans/2026-04-21-pizhi-milestone-11-agent-backend.md`: this plan; update observed verification notes if final execution results differ

### Task 1: Lock Backend-Aware Config And CLI Contracts

**Files:**
- Modify: `src/pizhi/core/config.py`
- Modify: `src/pizhi/cli.py`
- Modify: `src/pizhi/commands/provider_cmd.py`
- Create: `src/pizhi/commands/agent_cmd.py`
- Modify: `tests/unit/test_config.py`
- Modify: `tests/integration/test_provider_configure_command.py`
- Modify: `tests/integration/test_cli_help_contract.py`

- [ ] **Step 1: Write the failing config and CLI contract tests**

```python
def test_config_round_trip_supports_agent_backend_section(tmp_path):
    config = default_config(name="Test Novel")
    config.execution = ExecutionConfig(
        backend="agent",
        provider=None,
        agent=AgentBackendSection(
            agent_backend="opencode",
            agent_command="opencode",
            agent_args=["run", "--non-interactive"],
        ),
    )
    save_config(path, config)

    loaded = load_config(path)
    assert loaded.execution.backend == "agent"
    assert loaded.execution.agent.agent_backend == "opencode"


def test_provider_configure_command_keeps_legacy_provider_surface(initialized_project):
    result = run([sys.executable, "-m", "pizhi", "provider", "configure", ...], cwd=initialized_project)
    assert result.returncode == 0
    loaded = load_config(initialized_project / ".pizhi" / "config.yaml")
    assert loaded.execution.backend == "provider"


def test_agent_configure_command_writes_agent_backend_block(initialized_project):
    result = run(
        [sys.executable, "-m", "pizhi", "agent", "configure", "--agent-backend", "opencode", "--agent-command", "opencode"],
        cwd=initialized_project,
    )
    assert result.returncode == 0
```

- [ ] **Step 2: Run the targeted config/CLI tests to verify they fail**

Run:
`python -m pytest tests/unit/test_config.py tests/integration/test_provider_configure_command.py tests/integration/test_cli_help_contract.py -q --tb=short -rfE`

Expected:
- failures because no backend-aware config section exists yet
- failure because `agent configure` is not yet in the CLI

- [ ] **Step 3: Implement the minimal backend-aware config model and CLI entrypoint**

Add:

- a new execution config dataclass with `backend`, `provider`, and `agent` sections
- backward-compatible config loading that still accepts existing `provider:` blocks
- `agent configure` command support for the first `opencode` backend
- preserved `provider configure` behavior that now writes the provider backend inside the unified config model

- [ ] **Step 4: Re-run the targeted tests**

Run:
`python -m pytest tests/unit/test_config.py tests/integration/test_provider_configure_command.py tests/integration/test_cli_help_contract.py -q --tb=short -rfE`

Expected:
- selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/core/config.py src/pizhi/cli.py src/pizhi/commands/provider_cmd.py src/pizhi/commands/agent_cmd.py tests/unit/test_config.py tests/integration/test_provider_configure_command.py tests/integration/test_cli_help_contract.py
git commit -m "feat: add backend-aware execution config"
```

### Task 2: Introduce The Unified Execution Backend Contract

**Files:**
- Create: `src/pizhi/backends/base.py`
- Create: `src/pizhi/backends/provider_backend.py`
- Create: `src/pizhi/services/execution.py`
- Modify: `src/pizhi/services/provider_execution.py`
- Modify: `tests/unit/test_provider_execution.py`
- Create: `tests/unit/test_execution.py`

- [ ] **Step 1: Write the failing backend-selection and provider-regression tests**

```python
def test_execute_prompt_request_selects_provider_backend_from_execution_config(initialized_project, monkeypatch):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider_backend(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    result = execute_prompt_request(initialized_project, request, target="project", route_name="brainstorm")

    assert result.status == "succeeded"
    assert result.record.metadata["backend"] == "provider"


def test_execute_prompt_request_rejects_unknown_backend(initialized_project):
    config = load_config(initialized_project / ".pizhi" / "config.yaml")
    config.execution = ExecutionConfig(backend="unknown", provider=None, agent=None)
    save_config(initialized_project / ".pizhi" / "config.yaml", config)

    with pytest.raises(ValueError, match="unsupported execution backend"):
        execute_prompt_request(initialized_project, request, target="project")
```

- [ ] **Step 2: Run the targeted execution tests to verify they fail**

Run:
`python -m pytest tests/unit/test_provider_execution.py tests/unit/test_execution.py -q --tb=short -rfE`

Expected:
- failures because unified execution modules do not exist yet

- [ ] **Step 3: Implement the minimal execution abstraction**

Create:

- backend request/response protocol in `backends/base.py`
- provider backend adapter in `backends/provider_backend.py`
- unified `execute_prompt_request(...)` entrypoint in `services/execution.py`

Then either:

- keep `services/provider_execution.py` as a compatibility shim importing the new service

or

- update all current imports to the new service if the change stays mechanical and contained

- [ ] **Step 4: Re-run the targeted execution tests**

Run:
`python -m pytest tests/unit/test_provider_execution.py tests/unit/test_execution.py -q --tb=short -rfE`

Expected:
- selected tests `PASSED`
- provider-backed run metadata now records backend identity

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/backends/base.py src/pizhi/backends/provider_backend.py src/pizhi/services/execution.py src/pizhi/services/provider_execution.py tests/unit/test_provider_execution.py tests/unit/test_execution.py
git commit -m "feat: add unified execution backend contract"
```

### Task 3: Add `opencode` Task Packaging And Agent Backend Execution

**Files:**
- Create: `src/pizhi/backends/agent_backend.py`
- Create: `src/pizhi/backends/opencode_backend.py`
- Create: `src/pizhi/services/agent_task_package.py`
- Modify: `src/pizhi/services/run_store.py`
- Create: `tests/unit/test_agent_task_package.py`
- Create: `tests/unit/test_opencode_backend.py`
- Modify: `tests/unit/test_execution.py`

- [ ] **Step 1: Write the failing task-package and `opencode` backend tests**

```python
def test_render_agent_task_package_writes_expected_bridge_files(tmp_path):
    package = render_agent_task_package(...)

    assert package.request_path.name == "agent_request.json"
    assert package.task_path.name == "agent_task.md"
    assert package.skill_dir.joinpath("AGENTS.md").exists()


def test_opencode_backend_reads_candidate_from_agent_output_file(tmp_path, monkeypatch):
    backend = OpencodeBackend(command="opencode", args=["run", "--non-interactive"])
    monkeypatch.setattr(subprocess, "run", fake_completed_process_writing_output)

    response = backend.execute(request)

    assert response.content_text.startswith("##")
    assert response.raw_payload["backend"] == "opencode"


def test_opencode_backend_treats_missing_output_file_as_failure(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="agent output file was not produced"):
        backend.execute(request)
```

- [ ] **Step 2: Run the targeted task-package/backend tests to verify they fail**

Run:
`python -m pytest tests/unit/test_agent_task_package.py tests/unit/test_opencode_backend.py tests/unit/test_execution.py -q --tb=short -rfE`

Expected:
- failures because the task package service and agent backend do not exist yet

- [ ] **Step 3: Implement the file-bridge and backend execution path**

Implement:

- task package rendering into the run directory
- temporary one-run skill generation with explicit no-source-of-truth-mutation rules
- subprocess execution wrapper for `opencode`
- output-file ingestion from `agent_output.md`
- run-store metadata fields for backend kind, backend implementation, task path, output path, stdout path, and stderr path

- [ ] **Step 4: Re-run the targeted task-package/backend tests**

Run:
`python -m pytest tests/unit/test_agent_task_package.py tests/unit/test_opencode_backend.py tests/unit/test_execution.py -q --tb=short -rfE`

Expected:
- selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/backends/agent_backend.py src/pizhi/backends/opencode_backend.py src/pizhi/services/agent_task_package.py src/pizhi/services/run_store.py tests/unit/test_agent_task_package.py tests/unit/test_opencode_backend.py tests/unit/test_execution.py
git commit -m "feat: add opencode agent backend bridge"
```

### Task 4: Route Execute-Capable Commands And Continue Sessions Through The Unified Backend

**Files:**
- Modify: `src/pizhi/commands/brainstorm_cmd.py`
- Modify: `src/pizhi/commands/outline_cmd.py`
- Modify: `src/pizhi/commands/write_cmd.py`
- Modify: `src/pizhi/services/ai_review_service.py`
- Modify: `src/pizhi/services/continue_execution.py`
- Modify: `tests/integration/test_provider_execution_commands.py`
- Modify: `tests/unit/test_continue_execution.py`
- Modify: `tests/integration/test_review_command.py`

- [ ] **Step 1: Write the failing integration/regression tests for backend routing**

```python
def test_execute_commands_still_work_with_provider_backend(initialized_project, monkeypatch, capsys):
    _configure_provider_backend(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    exit_code = main(["brainstorm", "--execute"])

    assert exit_code == 0
    assert "Run ID:" in capsys.readouterr().out


def test_continue_execution_uses_agent_backend_when_project_requests_it(initialized_project, monkeypatch):
    _configure_opencode_backend(initialized_project)
    monkeypatch.setattr("pizhi.backends.opencode_backend.subprocess.run", fake_successful_agent_step)

    result = start_continue_execution(initialized_project, count=3)

    assert result.checkpoint is not None
    assert result.checkpoint.status == "generated"
```

- [ ] **Step 2: Run the targeted integration/unit tests to verify they fail**

Run:
`python -m pytest tests/integration/test_provider_execution_commands.py tests/unit/test_continue_execution.py tests/integration/test_review_command.py -q --tb=short -rfE`

Expected:
- failures because command and continue paths still call provider-only execution code

- [ ] **Step 3: Implement the minimal command/service routing changes**

Switch execute-capable commands and services to the unified execution entrypoint, while preserving:

- prompt-only behavior when `--execute` is omitted
- provider-backed regression behavior
- continue checkpoint generation semantics
- review execute sequencing and error handling

- [ ] **Step 4: Re-run the targeted tests**

Run:
`python -m pytest tests/integration/test_provider_execution_commands.py tests/unit/test_continue_execution.py tests/integration/test_review_command.py -q --tb=short -rfE`

Expected:
- selected tests `PASSED`
- provider backend regressions remain green
- continue remains resumable after backend failures

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/commands/brainstorm_cmd.py src/pizhi/commands/outline_cmd.py src/pizhi/commands/write_cmd.py src/pizhi/services/ai_review_service.py src/pizhi/services/continue_execution.py tests/integration/test_provider_execution_commands.py tests/unit/test_continue_execution.py tests/integration/test_review_command.py
git commit -m "feat: route execute flows through unified backends"
```

### Task 5: Update Public Docs And Repository-Shipped Playbook

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/ARCHITECTURE.md`
- Modify: `docs/guides/getting-started.md`
- Modify: `agents/pizhi/AGENTS.md`
- Modify: `agents/pizhi/resources/workflow.md`
- Modify: `tests/integration/test_docs_contract.py`

- [ ] **Step 1: Write the failing docs contract tests**

```python
def test_readme_documents_host_orchestrator_backend_split(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    assert "Claude Code" in readme
    assert "opencode" in readme
    assert "backend" in readme


def test_agent_playbook_clarifies_external_host_vs_backend(project_root):
    agents_md = (project_root / "agents" / "pizhi" / "AGENTS.md").read_text(encoding="utf-8")
    assert "drive the `pizhi` CLI" in agents_md
    assert "Do not change provider configuration unless the user asked." in agents_md
```

- [ ] **Step 2: Run the targeted docs tests to verify they fail**

Run:
`python -m pytest tests/integration/test_docs_contract.py -q --tb=short -rfE`

Expected:
- failures because docs still describe Pizhi primarily as provider-backed execution

- [ ] **Step 3: Update docs and the playbook**

Clarify:

- `Claude Code + skill` is the recommended host entry
- Pizhi is the orchestrator and source-of-truth manager
- `opencode` is the first agent execution backend
- backend choice affects `--execute`, not deterministic commands such as `apply`, `checkpoint`, or `compile`

- [ ] **Step 4: Re-run the targeted docs tests**

Run:
`python -m pytest tests/integration/test_docs_contract.py -q --tb=short -rfE`

Expected:
- selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add README.md docs/architecture/ARCHITECTURE.md docs/guides/getting-started.md agents/pizhi/AGENTS.md agents/pizhi/resources/workflow.md tests/integration/test_docs_contract.py
git commit -m "docs: describe agent backend architecture"
```

### Task 6: Verify Full Regression And Record Plan Notes

**Files:**
- Modify: `meta/plans/2026-04-21-pizhi-milestone-11-agent-backend.md`

- [ ] **Step 1: Run the full regression suite**

Run:
`python -m pytest tests/unit tests/integration -q --tb=short -rfE`

Expected:
- full suite `PASSED`

- [ ] **Step 2: Run CLI help validation**

Run:
`python -m pizhi --help`

Expected:
- CLI help prints the updated backend configuration entrypoint and existing commands without traceback

- [ ] **Step 3: Record the observed verification result in this plan**

If the final observed result differs from:

- `323 passed in 93.28s (0:01:33)`

record the observed result in a short execution note without rewriting the baseline instruction.

- [ ] **Step 4: Add a short execution note summarizing the milestone outcome**

Record that:

- execution is now backend-pluggable
- provider-backed execution still works
- `opencode` is available as the first agent backend
- external hosts still drive the CLI rather than replacing Pizhi orchestration

- [ ] **Step 5: Commit**

```bash
git add meta/plans/2026-04-21-pizhi-milestone-11-agent-backend.md
git commit -m "docs: record milestone 11 verification"
```

## Execution Note

- Final full regression on this branch: `python -m pytest tests/unit tests/integration -q --tb=short -rfE` -> `344 passed in 103.77s (0:01:43)`.
- Final CLI help validation: `python -m pizhi --help` printed the backend-aware command surface, including `provider` and `agent`, without traceback.
- Milestone 11 outcome:
  - execution is now backend-pluggable
  - provider-backed execution still works
  - `opencode` is available as the first agent backend
  - external hosts still drive the CLI rather than replacing Pizhi orchestration
