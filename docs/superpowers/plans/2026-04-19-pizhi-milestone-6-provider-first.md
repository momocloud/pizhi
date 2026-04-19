# Pizhi Milestone 6 Provider First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first real provider-backed execution path to Pizhi by supporting `--execute` for `brainstorm`, `outline expand`, and `write`, persisting auditable run artifacts, and exposing explicit `runs` / `apply --run-id` commands without breaking the existing prompt-only flow.

**Architecture:** Milestone 6 keeps command-specific prompt construction and deterministic apply logic inside the existing services, but inserts a shared provider-execution layer between prompt generation and source-of-truth mutation. Provider calls are OpenAI-compatible and write `prompt.md`, `raw.json`, `normalized.md`, and `manifest.json` into `.pizhi/cache/runs/<run_id>/`; truth-source updates still happen only through `pizhi apply --run-id ...`.

**Tech Stack:** Python 3.14, pytest, argparse, pathlib, dataclasses, stdlib `json`, stdlib `urllib.request`, Markdown text parsing, YAML config storage

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\milestone-6-provider-first`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -v`
  - Expected: current branch baseline passes cleanly in this worktree
  - Observed while writing this plan: `88 passed`

## File Map

- `src/pizhi/core/config.py`: extend project config with optional provider settings and tolerant loading for pre-milestone-6 projects
- `src/pizhi/core/paths.py`: add a dedicated `runs_dir` helper under `.pizhi/cache/runs/`
- `src/pizhi/cli.py`: register `provider`, `runs`, and `apply` commands plus `--execute` flags for `brainstorm`, `outline expand`, and `write`
- `src/pizhi/adapters/base.py`: keep shared prompt-request contracts stable for both prompt-only and provider-backed flows
- `src/pizhi/adapters/provider_base.py`: define provider request/response contracts and adapter interface
- `src/pizhi/adapters/openai_compatible.py`: send OpenAI-compatible chat-completions requests and normalize the returned message content
- `src/pizhi/adapters/__init__.py`: export the new provider adapter types
- `src/pizhi/services/run_store.py`: generate `run_id`, persist run directories and manifests, list runs, and load a single run
- `src/pizhi/services/provider_execution.py`: orchestrate provider config lookup, env var resolution, provider invocation, normalization, and run persistence
- `src/pizhi/services/apply_service.py`: map a successful `run_id` back onto the existing deterministic apply logic
- `src/pizhi/services/brainstorm_service.py`: expose prompt-request building and deterministic brainstorm apply behavior separately
- `src/pizhi/services/outline_service.py`: expose prompt-request building plus an apply-from-raw-response helper for outline runs
- `src/pizhi/services/write_service.py`: expose prompt-request building plus an apply-from-raw-response helper that still triggers milestone-5 maintenance
- `src/pizhi/commands/provider_cmd.py`: implement `pizhi provider configure` in interactive and parameter modes
- `src/pizhi/commands/runs_cmd.py`: print a compact list view of recent run manifests
- `src/pizhi/commands/apply_cmd.py`: validate `run_id` and dispatch to `apply_service`
- `src/pizhi/commands/brainstorm_cmd.py`: branch between prompt-only, provider-execute, and response-file application paths
- `src/pizhi/commands/outline_cmd.py`: branch between prompt-only, provider-execute, and response-file application paths
- `src/pizhi/commands/write_cmd.py`: branch between prompt-only, provider-execute, and response-file application paths
- `tests/unit/test_config.py`: provider config round-trip and missing-provider tolerance
- `tests/unit/test_run_store.py`: run-manifest persistence, listing order, and failed-run artifact coverage
- `tests/unit/test_openai_compatible.py`: request payload construction and content extraction from OpenAI-compatible responses
- `tests/unit/test_provider_execution.py`: missing-config, missing-env, provider-failure, normalization-failure, and success flows
- `tests/unit/test_apply_service.py`: `run_id` validation and routing to existing deterministic apply helpers
- `tests/integration/test_provider_configure_command.py`: parameter-mode and interactive provider configuration updates
- `tests/integration/test_runs_command.py`: readable run-list output for persisted manifests
- `tests/integration/test_apply_command.py`: `apply --run-id` success and rejection cases
- `tests/integration/test_provider_execution_commands.py`: `brainstorm`, `outline expand`, and `write` `--execute` flows using a stubbed provider adapter

### Task 1: Extend Project Config And Provider CLI Surface

**Files:**
- Modify: `src/pizhi/core/config.py`
- Modify: `src/pizhi/core/paths.py`
- Modify: `src/pizhi/cli.py`
- Create: `src/pizhi/commands/provider_cmd.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/integration/test_provider_configure_command.py`

- [ ] **Step 1: Write the failing tests for provider config round-trip and configure command behavior**

```python
def test_config_round_trip_preserves_provider_settings(tmp_path):
    config = default_config(name="Test Novel")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    save_config(path, config)

    loaded = load_config(path)
    assert loaded.provider.model == "gpt-5.4"
    assert loaded.provider.api_key_env == "OPENAI_API_KEY"


def test_provider_configure_command_writes_provider_block(initialized_project):
    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "provider",
            "configure",
            "--provider",
            "openai_compatible",
            "--model",
            "gpt-5.4",
            "--base-url",
            "https://api.openai.com/v1",
            "--api-key-env",
            "OPENAI_API_KEY",
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "provider:" in (initialized_project / ".pizhi" / "config.yaml").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_config.py tests/integration/test_provider_configure_command.py -v`

Expected:
- config test fails because `ProjectConfig` has no provider section
- CLI test fails because `provider configure` is not registered

- [ ] **Step 3: Implement optional provider config, `runs_dir`, and `provider configure`**

```python
@dataclass(slots=True)
class ProviderSection:
    provider: str
    model: str
    base_url: str
    api_key_env: str


@dataclass(slots=True)
class ProjectConfig:
    ...
    provider: ProviderSection | None = None
```

```python
provider_parser = subparsers.add_parser("provider", help="configure provider settings")
provider_subparsers = provider_parser.add_subparsers(dest="provider_command")
provider_configure_parser = provider_subparsers.add_parser("configure", help="create or update provider config")
provider_configure_parser.add_argument("--provider")
provider_configure_parser.add_argument("--model")
provider_configure_parser.add_argument("--base-url")
provider_configure_parser.add_argument("--api-key-env")
provider_configure_parser.set_defaults(handler=run_provider_configure)
```

```python
def run_provider_configure(args: argparse.Namespace) -> int:
    config = load_config(paths.config_file)
    provider_section = _resolve_provider_answers(args)
    config.provider = provider_section
    save_config(paths.config_file, config)
    print(f"Provider configured: {provider_section.provider} {provider_section.model}")
    return 0
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_config.py tests/integration/test_provider_configure_command.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/core/config.py src/pizhi/core/paths.py src/pizhi/cli.py src/pizhi/commands/provider_cmd.py tests/unit/test_config.py tests/integration/test_provider_configure_command.py
git commit -m "feat: add provider configuration command"
```

### Task 2: Add Run Store And OpenAI-Compatible Adapter Primitives

**Files:**
- Create: `src/pizhi/adapters/provider_base.py`
- Create: `src/pizhi/adapters/openai_compatible.py`
- Modify: `src/pizhi/adapters/__init__.py`
- Create: `src/pizhi/services/run_store.py`
- Test: `tests/unit/test_openai_compatible.py`
- Test: `tests/unit/test_run_store.py`

- [ ] **Step 1: Write the failing unit tests for payload construction and run persistence**

```python
def test_openai_compatible_adapter_builds_chat_completions_request():
    request = ProviderRequest(
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key="secret",
        prompt_text="# Prompt",
    )
    prepared = build_http_request(request)

    assert prepared.full_url == "https://api.openai.com/v1/chat/completions"
    assert prepared.headers["Authorization"] == "Bearer secret"


def test_run_store_persists_successful_run(tmp_path):
    store = RunStore(tmp_path / ".pizhi" / "cache" / "runs")
    record = store.write_success(
        command="write",
        target="ch001",
        prompt_text="# Prompt",
        raw_payload={"id": "resp_123"},
        normalized_text="## normalized\n",
        metadata={"provider": "openai_compatible"},
    )

    assert (record.run_dir / "manifest.json").exists()
    assert (record.run_dir / "raw.json").exists()
    assert (record.run_dir / "normalized.md").exists()
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_openai_compatible.py tests/unit/test_run_store.py -v`

Expected: FAIL with import errors because the adapter and run store do not exist yet

- [ ] **Step 3: Implement provider contracts, OpenAI-compatible HTTP adapter, and run persistence**

```python
@dataclass(frozen=True, slots=True)
class ProviderRequest:
    model: str
    base_url: str
    api_key: str
    prompt_text: str


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    raw_payload: dict[str, Any]
    content_text: str
```

```python
payload = {
    "model": request.model,
    "messages": [{"role": "user", "content": request.prompt_text}],
}
http_request = Request(
    f"{request.base_url.rstrip('/')}/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {request.api_key}",
        "Content-Type": "application/json",
    },
    method="POST",
)
```

```python
manifest = {
    "run_id": run_id,
    "command": command,
    "target": target,
    "status": status,
    "created_at": created_at,
    "provider": metadata["provider"],
    "model": metadata["model"],
    "base_url": metadata["base_url"],
    "metadata": metadata,
    "referenced_files": referenced_files,
}
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_openai_compatible.py tests/unit/test_run_store.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/adapters/provider_base.py src/pizhi/adapters/openai_compatible.py src/pizhi/adapters/__init__.py src/pizhi/services/run_store.py tests/unit/test_openai_compatible.py tests/unit/test_run_store.py
git commit -m "feat: add provider adapter and run store primitives"
```

### Task 3: Build Shared Provider Execution And Refactor Command Services

**Files:**
- Create: `src/pizhi/services/provider_execution.py`
- Modify: `src/pizhi/services/brainstorm_service.py`
- Modify: `src/pizhi/services/outline_service.py`
- Modify: `src/pizhi/services/write_service.py`
- Test: `tests/unit/test_provider_execution.py`

- [ ] **Step 1: Write the failing unit tests for missing config, missing env, provider failure, and success**

```python
def test_execute_prompt_request_requires_provider_config(initialized_project):
    request = BrainstormService(initialized_project).build_prompt_request()
    with pytest.raises(ValueError, match="provider is not configured"):
        execute_prompt_request(initialized_project, request, target="project")


def test_execute_prompt_request_persists_failed_provider_run(initialized_project, monkeypatch):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr("pizhi.services.provider_execution.build_provider_adapter", lambda *_: FailingAdapter())

    result = execute_prompt_request(initialized_project, request, target="ch001")
    assert result.status == "provider_failed"
    assert result.run_dir.joinpath("error.txt").exists()


def test_execute_prompt_request_persists_normalized_success(initialized_project, monkeypatch):
    request = BrainstormService(initialized_project).build_prompt_request()
    _configure_provider(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr("pizhi.services.provider_execution.build_provider_adapter", lambda *_: StubAdapter("## synopsis\n..."))

    result = execute_prompt_request(initialized_project, request, target="project")
    assert result.status == "succeeded"
    assert result.run_dir.joinpath("normalized.md").read_text(encoding="utf-8").startswith("##")
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_provider_execution.py -v`

Expected: FAIL because `provider_execution.py` and command-service request builders do not exist

- [ ] **Step 3: Implement the shared execution service and refactor services to expose request/apply boundaries**

```python
def execute_prompt_request(project_root: Path, request: PromptRequest, target: str) -> ExecutionResult:
    provider_config = _load_provider_config(project_root)
    api_key = _load_api_key(provider_config.api_key_env)
    response = adapter.execute(
        ProviderRequest(
            model=provider_config.model,
            base_url=provider_config.base_url,
            api_key=api_key,
            prompt_text=request.prompt_text,
        )
    )
    normalized_text = _normalize_provider_content(response.content_text)
    return run_store.write_success(...)
```

```python
class BrainstormService:
    def build_prompt_request(self) -> PromptRequest:
        return PromptRequest(
            command_name="brainstorm",
            prompt_text=self._build_prompt(),
            metadata={"command": "brainstorm"},
            referenced_files=[...],
        )

    def prepare_prompt(self, request: PromptRequest) -> PromptArtifact:
        return self.adapter.prepare(request)
```

```python
class WriteService:
    def build_prompt_request(self, chapter_number: int) -> PromptRequest:
        context = build_chapter_context(self.project_root, chapter_number)
        synopsis_coverage = _load_synopsis_coverage_prompt_context(self.project_root)
        return PromptRequest(
            command_name="write",
            prompt_text=_build_prompt(context, synopsis_coverage),
            metadata={"chapter": chapter_number},
            referenced_files=[...],
        )

    def apply_response(self, chapter_number: int, raw_response: str) -> ChapterWriteResult:
        chapter_result = apply_chapter_response(...)
        run_after_write(self.project_root)
        return chapter_result
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_provider_execution.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/provider_execution.py src/pizhi/services/brainstorm_service.py src/pizhi/services/outline_service.py src/pizhi/services/write_service.py tests/unit/test_provider_execution.py
git commit -m "feat: add shared provider execution service"
```

### Task 4: Wire `--execute` Into Brainstorm, Outline Expand, And Write

**Files:**
- Modify: `src/pizhi/cli.py`
- Modify: `src/pizhi/commands/brainstorm_cmd.py`
- Modify: `src/pizhi/commands/outline_cmd.py`
- Modify: `src/pizhi/commands/write_cmd.py`
- Test: `tests/integration/test_provider_execution_commands.py`

- [ ] **Step 1: Write the failing integration tests for the three `--execute` entry points**

```python
def test_brainstorm_execute_writes_run_id_and_run_artifacts(initialized_project, monkeypatch):
    monkeypatch.chdir(initialized_project)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    _configure_provider(initialized_project)
    monkeypatch.setattr("pizhi.services.provider_execution.build_provider_adapter", lambda *_: StubAdapter("## synopsis\n..."))

    exit_code = main(["brainstorm", "--execute"])
    assert exit_code == 0
    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"
    assert any(path.joinpath("normalized.md").exists() for path in runs_dir.iterdir())


def test_write_execute_keeps_prompt_only_flow_when_execute_is_omitted(initialized_project, monkeypatch):
    monkeypatch.chdir(initialized_project)
    exit_code = main(["write", "--chapter", "1"])
    assert exit_code == 0
    assert (initialized_project / ".pizhi" / "cache" / "prompts").exists()
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_provider_execution_commands.py -v`

Expected:
- execute tests fail because the new flag is not registered
- prompt-only regression assertion may fail if command branching is not implemented yet

- [ ] **Step 3: Implement CLI branching for provider-backed execution**

```python
brainstorm_parser.add_argument("--execute", action="store_true", help="call the configured provider")
outline_expand_parser.add_argument("--execute", action="store_true", help="call the configured provider")
write_parser.add_argument("--execute", action="store_true", help="call the configured provider")
```

```python
if args.execute:
    request = service.build_prompt_request(...)
    prompt_artifact = service.prepare_prompt(request)
    execution = execute_prompt_request(service.project_root, request, target=f"ch{args.chapter:03d}")
    print(f"Prepared prompt packet: {prompt_artifact.prompt_path.name}")
    print(f"Run ID: {execution.run_id}")
    return 0
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/integration/test_provider_execution_commands.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/cli.py src/pizhi/commands/brainstorm_cmd.py src/pizhi/commands/outline_cmd.py src/pizhi/commands/write_cmd.py tests/integration/test_provider_execution_commands.py
git commit -m "feat: add execute mode for prompt commands"
```

### Task 5: Add `runs` Listing And `apply --run-id` Routing

**Files:**
- Create: `src/pizhi/services/apply_service.py`
- Create: `src/pizhi/commands/runs_cmd.py`
- Create: `src/pizhi/commands/apply_cmd.py`
- Modify: `src/pizhi/cli.py`
- Test: `tests/unit/test_apply_service.py`
- Test: `tests/integration/test_runs_command.py`
- Test: `tests/integration/test_apply_command.py`

- [ ] **Step 1: Write the failing tests for run listing and deterministic apply routing**

```python
def test_apply_run_routes_successful_write_run(initialized_project):
    run_id = _seed_successful_run(initialized_project, command="write", target="ch001", normalized_text=fixture_text("ch001_response.md"))
    result = apply_run(initialized_project, run_id)

    assert result.command == "write"
    assert (initialized_project / ".pizhi" / "chapters" / "ch001" / "text.md").exists()


def test_apply_command_rejects_non_success_run(initialized_project):
    run_id = _seed_failed_run(initialized_project, status="provider_failed")
    result = run(
        [sys.executable, "-m", "pizhi", "apply", "--run-id", run_id],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "status is provider_failed" in result.stderr


def test_runs_command_lists_recent_runs(initialized_project):
    _seed_successful_run(initialized_project, command="brainstorm", target="project")
    result = run(
        [sys.executable, "-m", "pizhi", "runs"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "brainstorm" in result.stdout
    assert "succeeded" in result.stdout
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_apply_service.py tests/integration/test_runs_command.py tests/integration/test_apply_command.py -v`

Expected: FAIL because neither the command handlers nor the apply service exist

- [ ] **Step 3: Implement run listing, `apply --run-id`, and command routing**

```python
def apply_run(project_root: Path, run_id: str) -> ApplyResult:
    record = RunStore(project_paths(project_root).runs_dir).load(run_id)
    if record.status != "succeeded":
        raise ValueError(f"run {run_id} status is {record.status}")

    normalized_text = record.normalized_path.read_text(encoding="utf-8")
    if record.command == "brainstorm":
        BrainstormService(project_root).apply_response(normalized_text)
    elif record.command == "outline-expand":
        OutlineService(project_root).apply_response(normalized_text)
    elif record.command == "write":
        WriteService(project_root).apply_response(record.metadata["chapter"], normalized_text)
    else:
        raise ValueError(f"unsupported run command: {record.command}")
```

```python
def run_runs(args: argparse.Namespace) -> int:
    for record in RunStore(project_paths(Path.cwd()).runs_dir).list_runs():
        print(f"{record.run_id}  {record.command}  {record.target}  {record.status}  {record.created_at}")
    return 0
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_apply_service.py tests/integration/test_runs_command.py tests/integration/test_apply_command.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/apply_service.py src/pizhi/commands/runs_cmd.py src/pizhi/commands/apply_cmd.py src/pizhi/cli.py tests/unit/test_apply_service.py tests/integration/test_runs_command.py tests/integration/test_apply_command.py
git commit -m "feat: add run listing and explicit apply command"
```

### Task 6: Final Verification And Plan State Update

**Files:**
- Modify: `docs/superpowers/plans/2026-04-19-pizhi-milestone-6-provider-first.md`

- [ ] **Step 1: Run command smoke tests**

Run:
- `python -m pizhi provider configure --help`
- `python -m pizhi runs --help`
- `python -m pizhi apply --help`
- `python -m pizhi brainstorm --help`
- `python -m pizhi outline expand --help`
- `python -m pizhi write --help`

Expected: all commands exit `0`

- [ ] **Step 2: Run the full test suite**

Run:
`python -m pytest tests/unit tests/integration -v`

Expected: all tests `PASSED` and count increases beyond the 88-test baseline

- [ ] **Step 3: Mark verification steps complete in this plan**

Update this file so the executed verification boxes are checked and add the final observed command/test results near Task 6.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-19-pizhi-milestone-6-provider-first.md
git commit -m "docs: record milestone 6 verification state"
```
