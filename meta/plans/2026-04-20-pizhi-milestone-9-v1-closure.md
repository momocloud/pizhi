# Pizhi Milestone 9 V1 Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining v1 gaps by adding fixed per-command model routing, expanding `compile` to volume/chapter/range targets, and hardening the existing provider-first flows without changing the snapshot contract.

**Architecture:** Milestone 9 keeps the existing provider and storage layers intact, but adds a shared route-resolution layer on top of provider config so commands pick stable project-level models without ad hoc CLI overrides. `compile` is expanded through one target-aware compiler path, and the architecture docs are updated to mark the snapshot-format question as closed for v1.

**Tech Stack:** Python 3.14, pytest, argparse, pathlib, dataclasses, existing provider execution/run store, existing continue checkpoint orchestration, Markdown/frontmatter/index.jsonl persistence

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\milestone-9-v1-closure`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -q --tb=short -rfE`
  - Observed while writing this plan: `238 passed in 70.88s`
  - Observed during Task 5 verification: `261 passed in 76.57s`

## File Map

- `src/pizhi/core/config.py`: extend `ProviderSection` with per-command model route fields and shared provider-config resolution helpers while preserving existing review connection overrides
- `src/pizhi/commands/provider_cmd.py`: persist the new route fields in interactive and parameter modes without regressing current review override behavior
- `src/pizhi/services/provider_execution.py`: resolve routed provider config by command family, keep explicit `provider_config` override behavior, and record the actual selected model in run metadata
- `src/pizhi/commands/brainstorm_cmd.py`: request provider execution through the `brainstorm` route
- `src/pizhi/commands/outline_cmd.py`: request provider execution through the `outline` route
- `src/pizhi/commands/write_cmd.py`: request provider execution through the `write` route
- `src/pizhi/services/continue_execution.py`: route both outline and write checkpoint generation through the shared `continue` model
- `src/pizhi/services/ai_review_service.py`: route review execution through the shared `review` route while preserving review-specific base URL and API key fallback
- `src/pizhi/cli.py`: add compile target arguments as a mutually exclusive group
- `src/pizhi/commands/compile_cmd.py`: validate compile target selection and call the compiler with an explicit target contract
- `src/pizhi/services/compiler.py`: introduce target-aware compile logic for volume, single chapter, and continuous chapter range outputs, with strict failure behavior
- `docs/architecture/ARCHITECTURE.md`: close the snapshot-format open question and document the v1 model-routing / compile-granularity decisions
- `tests/unit/test_config.py`: cover route-field round-trip and route-resolution fallback behavior
- `tests/integration/test_provider_configure_command.py`: cover interactive and parameter-driven persistence of route fields
- `tests/unit/test_provider_execution.py`: cover routed provider selection, fallback, and explicit-override precedence
- `tests/integration/test_provider_execution_commands.py`: cover `brainstorm / outline / write` selecting the configured routed model
- `tests/unit/test_continue_execution.py`: cover `continue_model` being used for both outline and write checkpoint phases
- `tests/unit/test_ai_review_service.py`: cover routed review model selection plus deterministic prompt ordering
- `tests/unit/test_review_documents.py`: add malformed/duplicate machine-section regression coverage
- `tests/unit/test_compiler.py`: cover target-aware compiler behavior and strict failure semantics
- `tests/integration/test_compile_command.py`: cover `compile --volume`, `compile --chapter`, `compile --chapters`, and target-validation failures
- `meta/plans/2026-04-20-pizhi-milestone-9-v1-closure.md`: mark verification results after execution

### Task 1: Add Fixed Model Routing To Provider Config

**Files:**
- Modify: `src/pizhi/core/config.py`
- Modify: `src/pizhi/commands/provider_cmd.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/integration/test_provider_configure_command.py`

- [ ] **Step 1: Write the failing config and provider-configure tests**

```python
def test_config_round_trip_includes_route_level_model_fields(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)

    config = default_config(name="Test Novel")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        review_model="gpt-5.4-mini",
        review_base_url="https://api.openai.com/v1/review",
        review_api_key_env="OPENAI_REVIEW_API_KEY",
        brainstorm_model="gpt-5.4-large",
        outline_model="gpt-5.4-outline",
        write_model="gpt-5.4-write",
        continue_model="gpt-5.4-continue",
    )
    save_config(path, config)

    loaded = load_config(path)
    assert loaded.provider is not None
    assert loaded.provider.brainstorm_model == "gpt-5.4-large"
    assert loaded.provider.continue_model == "gpt-5.4-continue"


def test_provider_section_resolve_route_config_falls_back_to_default_model():
    provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        outline_model=None,
    )

    resolved = provider.resolve_route_config("outline")

    assert resolved.model == "gpt-5.4"
    assert resolved.base_url == "https://api.openai.com/v1"


def test_provider_configure_command_writes_route_level_model_fields(initialized_project):
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
            "--brainstorm-model",
            "gpt-5.4-large",
            "--outline-model",
            "gpt-5.4-outline",
            "--write-model",
            "gpt-5.4-write",
            "--continue-model",
            "gpt-5.4-continue",
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    loaded = load_config(initialized_project / ".pizhi" / "config.yaml")
    assert loaded.provider is not None
    assert loaded.provider.write_model == "gpt-5.4-write"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_config.py tests/integration/test_provider_configure_command.py -q --tb=short -rfE`

Expected:
- failures because route-level model fields and CLI options do not exist yet

- [ ] **Step 3: Implement route-level model fields and shared config resolution**

```python
@dataclass(slots=True)
class ProviderSection:
    provider: str
    model: str
    base_url: str
    api_key_env: str
    review_model: str | None = None
    review_base_url: str | None = None
    review_api_key_env: str | None = None
    brainstorm_model: str | None = None
    outline_model: str | None = None
    write_model: str | None = None
    continue_model: str | None = None

    def resolve_route_config(self, route_name: str) -> ProviderSection:
        if route_name == "review":
            base = self.resolve_review_config()
            return ProviderSection(
                provider=base.provider,
                model=self.review_model or base.model,
                base_url=base.base_url,
                api_key_env=base.api_key_env,
            )
        route_models = {
            "brainstorm": self.brainstorm_model,
            "outline": self.outline_model,
            "write": self.write_model,
            "continue": self.continue_model,
        }
        return ProviderSection(
            provider=self.provider,
            model=route_models.get(route_name) or self.model,
            base_url=self.base_url,
            api_key_env=self.api_key_env,
        )
```

```python
provider_configure_parser.add_argument("--brainstorm-model", help="brainstorm model name")
provider_configure_parser.add_argument("--outline-model", help="outline model name")
provider_configure_parser.add_argument("--write-model", help="write model name")
provider_configure_parser.add_argument("--continue-model", help="continue model name")
```

```python
provider_section = ProviderSection(
    provider=...,
    model=...,
    base_url=...,
    api_key_env=...,
    review_model=...,
    review_base_url=...,
    review_api_key_env=...,
    brainstorm_model=args.brainstorm_model if args.brainstorm_model is not None else existing.brainstorm_model,
    outline_model=args.outline_model if args.outline_model is not None else existing.outline_model,
    write_model=args.write_model if args.write_model is not None else existing.write_model,
    continue_model=args.continue_model if args.continue_model is not None else existing.continue_model,
)
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_config.py tests/integration/test_provider_configure_command.py -q --tb=short -rfE`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/core/config.py src/pizhi/commands/provider_cmd.py tests/unit/test_config.py tests/integration/test_provider_configure_command.py
git commit -m "feat: add fixed provider model routing config"
```

### Task 2: Route Provider Execution For Command Families

**Files:**
- Modify: `src/pizhi/services/provider_execution.py`
- Modify: `src/pizhi/commands/brainstorm_cmd.py`
- Modify: `src/pizhi/commands/outline_cmd.py`
- Modify: `src/pizhi/commands/write_cmd.py`
- Modify: `src/pizhi/services/ai_review_service.py`
- Test: `tests/unit/test_provider_execution.py`
- Test: `tests/integration/test_provider_execution_commands.py`
- Test: `tests/unit/test_ai_review_service.py`

- [ ] **Step 1: Write the failing routed-execution tests**

```python
def test_execute_prompt_request_uses_route_config_when_route_name_is_provided(initialized_project, monkeypatch):
    request = BrainstormService(initialized_project).build_prompt_request()
    config = load_config(initialized_project / ".pizhi" / "config.yaml")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="default-model",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        brainstorm_model="brainstorm-model",
    )
    save_config(initialized_project / ".pizhi" / "config.yaml", config)

    captured = {}

    class RecordingAdapter:
        def execute(self, provider_request):
            captured["provider_request"] = provider_request
            return ProviderResponse(raw_payload={"id": "resp_test"}, content_text="## synopsis\n...")

    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr("pizhi.services.provider_execution.build_provider_adapter", lambda *_: RecordingAdapter())

    result = execute_prompt_request(initialized_project, request, target="project", route_name="brainstorm")

    assert result.record.metadata["model"] == "brainstorm-model"
    assert captured["provider_request"].model == "brainstorm-model"


@pytest.mark.parametrize(
    ("argv", "route_model"),
    [
        (["brainstorm", "--execute"], "brainstorm-model"),
        (["outline", "expand", "--chapters", "1-2", "--execute"], "outline-model"),
        (["write", "--chapter", "1", "--execute"], "write-model"),
    ],
)
def test_execute_uses_route_level_models(initialized_project, monkeypatch, capsys, argv, route_model):
    ...
    assert route_model in captured_models


def test_run_ai_review_uses_review_route_and_preserves_review_connection_override(initialized_project, monkeypatch):
    ...
    assert provider_request.model == "gpt-5.4-mini"
    assert provider_request.base_url == "https://api.openai.com/v1/review"
    assert provider_request.api_key == "review-secret"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_provider_execution.py tests/integration/test_provider_execution_commands.py tests/unit/test_ai_review_service.py -q --tb=short -rfE`

Expected:
- failures because `execute_prompt_request()` does not accept a route name and command callers always use the default model

- [ ] **Step 3: Implement shared route resolution and route-aware command callers**

```python
def execute_prompt_request(
    project_root: Path,
    request: PromptRequest,
    target: str,
    provider_config: ProviderSection | None = None,
    route_name: str | None = None,
) -> ExecutionResult:
    provider_config = provider_config or _load_provider_config(project_root, route_name=route_name)
    ...
```

```python
def _load_provider_config(project_root: Path, route_name: str | None = None) -> ProviderSection:
    config = load_config(project_paths(project_root).config_file)
    if config.provider is None:
        raise ValueError("provider is not configured")
    if route_name is None:
        return config.provider
    return config.provider.resolve_route_config(route_name)
```

```python
execution = execute_prompt_request(service.project_root, request, target="project", route_name="brainstorm")
execution = execute_prompt_request(service.project_root, request, target=target, route_name="outline")
execution = execute_prompt_request(service.project_root, request, target=f"ch{args.chapter:03d}", route_name="write")
execution = execute_prompt_request(project_root, prompt_request, target=context.target, route_name="review")
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_provider_execution.py tests/integration/test_provider_execution_commands.py tests/unit/test_ai_review_service.py -q --tb=short -rfE`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/provider_execution.py src/pizhi/commands/brainstorm_cmd.py src/pizhi/commands/outline_cmd.py src/pizhi/commands/write_cmd.py src/pizhi/services/ai_review_service.py tests/unit/test_provider_execution.py tests/integration/test_provider_execution_commands.py tests/unit/test_ai_review_service.py
git commit -m "feat: route provider execution by command family"
```

### Task 3: Route `continue` Checkpoints And Harden Deterministic Review Output

**Files:**
- Modify: `src/pizhi/services/continue_execution.py`
- Modify: `src/pizhi/services/ai_review_service.py`
- Modify: `src/pizhi/services/review_documents.py`
- Test: `tests/unit/test_continue_execution.py`
- Test: `tests/unit/test_ai_review_service.py`
- Test: `tests/unit/test_review_documents.py`

- [ ] **Step 1: Write the failing continue-routing and determinism tests**

```python
def test_start_continue_execution_uses_continue_route_model(initialized_project, monkeypatch):
    _configure_provider_with_continue_model(initialized_project, continue_model="gpt-5.4-continue")
    ...
    result = start_continue_execution(initialized_project, count=3, direction="push the dock war")
    run_record = RunStore(project_paths(initialized_project).runs_dir).load(result.checkpoint.run_ids[0])
    assert run_record.metadata["model"] == "gpt-5.4-continue"


def test_resume_continue_execution_uses_continue_route_model_for_write_checkpoint(initialized_project, monkeypatch):
    _configure_provider_with_continue_model(initialized_project, continue_model="gpt-5.4-continue")
    ...
    result = resume_continue_execution(initialized_project, session.session_id)
    records = [RunStore(...).load(run_id) for run_id in result.checkpoint.run_ids]
    assert {record.metadata["model"] for record in records} == {"gpt-5.4-continue"}


def test_build_ai_review_prompt_sorts_metadata_and_referenced_files_deterministically():
    context = AIReviewContext(
        scope="chapter",
        target="ch002",
        prompt_context="...",
        referenced_files=[".pizhi/global/worldview.md", ".pizhi/chapters/ch001/text.md"],
        metadata={"zeta": 2, "alpha": 1},
    )

    prompt = build_ai_review_prompt(context)

    assert prompt.index("- .pizhi/chapters/ch001/text.md") < prompt.index("- .pizhi/global/worldview.md")
    assert prompt.index("- alpha: 1") < prompt.index("- zeta: 2")


def test_load_chapter_review_notes_collapses_duplicate_machine_headings_into_author_notes(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## A 类结构检查\n\n旧 A。\n\n## A 类结构检查\n\n重复 A。\n\n## B 类 AI 审查\n\n旧 B。\n",
        encoding="utf-8",
        newline="\n",
    )

    loaded = load_chapter_review_notes(notes_path)
    write_chapter_review_notes(notes_path, author_notes=loaded.author_notes, structural_markdown="新 A。\n", ai_review_markdown="新 B。\n")

    raw = notes_path.read_text(encoding="utf-8")
    assert raw.count("## A 类结构检查") == 1
    assert "重复 A。" in raw
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_continue_execution.py tests/unit/test_ai_review_service.py tests/unit/test_review_documents.py -q --tb=short -rfE`

Expected:
- failures because continue checkpoints still use the default model and review prompt / malformed section handling are not locked down tightly enough

- [ ] **Step 3: Implement routed continue execution and deterministic review-output ordering**

```python
execution = execute_prompt_request(
    project_root,
    request,
    target=target,
    route_name="continue",
)
```

```python
def _render_referenced_files(referenced_files: list[str]) -> list[str]:
    if not referenced_files:
        return ["- (none)"]
    return [f"- {path}" for path in sorted(referenced_files)]


def _render_metadata(metadata: dict[str, object]) -> list[str]:
    if not metadata:
        return ["- (none)"]
    return [f"- {key}: {metadata[key]}" for key in sorted(metadata)]
```

```python
if name in sections and name in {"A 类结构检查", "B 类 AI 审查", "一致性检查结果"}:
    author_parts.append(raw[match.start():end])
    continue
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_continue_execution.py tests/unit/test_ai_review_service.py tests/unit/test_review_documents.py -q --tb=short -rfE`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/continue_execution.py src/pizhi/services/ai_review_service.py src/pizhi/services/review_documents.py tests/unit/test_continue_execution.py tests/unit/test_ai_review_service.py tests/unit/test_review_documents.py
git commit -m "feat: route continue execution and harden review determinism"
```

### Task 4: Expand `compile` To Volume, Single Chapter, And Range Targets

**Files:**
- Modify: `src/pizhi/cli.py`
- Modify: `src/pizhi/commands/compile_cmd.py`
- Modify: `src/pizhi/services/compiler.py`
- Create: `tests/unit/test_compiler.py`
- Modify: `tests/integration/test_compile_command.py`

- [ ] **Step 1: Write the failing compiler and CLI tests**

```python
def test_compile_manuscript_writes_single_chapter_output(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    written = compile_manuscript(initialized_project, target=CompileTarget.single_chapter(1))

    assert written == [initialized_project / "manuscript" / "ch001.md"]
    assert "雨夜访客" in written[0].read_text(encoding="utf-8")


def test_compile_manuscript_writes_range_output_and_only_marks_target_chapters_compiled(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    apply_chapter_response(initialized_project, 3, fixture_text("ch001_response.md"))

    compile_manuscript(initialized_project, target=CompileTarget.chapter_range(2, 3))

    store = ChapterIndexStore(project_paths(initialized_project).chapter_index_file)
    by_number = {int(record["n"]): record for record in store.read_all()}
    assert by_number[1]["status"] == "drafted"
    assert by_number[2]["status"] == "compiled"
    assert by_number[3]["status"] == "compiled"


def test_compile_command_rejects_multiple_targets(initialized_project):
    result = run(
        [sys.executable, "-m", "pizhi", "compile", "--volume", "1", "--chapter", "1"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "exactly one" in result.stderr.lower()
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_compiler.py tests/integration/test_compile_command.py -q --tb=short -rfE`

Expected:
- failures because `compile` has no target arguments and the compiler only supports volume-wide output

- [ ] **Step 3: Implement target-aware compile selection and strict failure behavior**

```python
group = compile_parser.add_mutually_exclusive_group(required=True)
group.add_argument("--volume", type=int, help="compile a single volume")
group.add_argument("--chapter", type=int, help="compile a single chapter")
group.add_argument("--chapters", help="compile a continuous chapter range such as 11-15")
```

```python
@dataclass(frozen=True, slots=True)
class CompileTarget:
    mode: str
    start: int
    end: int | None = None

    @classmethod
    def single_volume(cls, volume: int) -> CompileTarget: ...
    @classmethod
    def single_chapter(cls, chapter: int) -> CompileTarget: ...
    @classmethod
    def chapter_range(cls, start: int, end: int) -> CompileTarget: ...
```

```python
def compile_manuscript(project_root: Path, *, target: CompileTarget) -> list[Path]:
    records = _select_compilable_records(store.read_all(), target)
    _ensure_records_have_text(paths, records)
    destination = _destination_for_target(paths.manuscript_dir, target)
    ...
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_compiler.py tests/integration/test_compile_command.py -q --tb=short -rfE`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/cli.py src/pizhi/commands/compile_cmd.py src/pizhi/services/compiler.py tests/unit/test_compiler.py tests/integration/test_compile_command.py
git commit -m "feat: add targeted compile modes"
```

### Task 5: Close Architecture Docs And Verify Milestone 9 End To End

**Files:**
- Modify: `docs/architecture/ARCHITECTURE.md`
- Modify: `meta/plans/2026-04-20-pizhi-milestone-9-v1-closure.md`

- [x] **Step 1: Update the architecture document to close the v1 open question**

```markdown
1. **快照格式**：~~当前定义为 Markdown。是否在某些字段引入 YAML 以提升程序解析稳定性？~~ **已决定**：v1 保持 `Markdown + frontmatter + index.jsonl`，不做快照制式迁移。
2. **多模型配置**：~~是否允许灵感模式用强模型、正文扩写用快模型？~~ **已决定**：允许，通过项目级固定模型路由配置到 `brainstorm / outline / write / continue / review`。
5. **manuscript 编译粒度**：~~当前按卷编译。是否支持按章、按自定义范围编译？~~ **已决定**：支持按卷、单章、连续章节范围编译。
```

- [x] **Step 2: Run command smoke tests for the new surfaces**

Run:
- `python -m pizhi provider configure --help`
- `python -m pizhi compile --help`
- `python -m pizhi continue --help`

Expected:
- all commands exit `0`
- `provider configure --help` prints the new route-model flags
- `compile --help` prints `--volume`, `--chapter`, and `--chapters`

Observed:
- `provider configure --help`: exit `0`; help text lists `--brainstorm-model`, `--outline-model`, `--write-model`, `--continue-model`, `--review-model`, `--review-base-url`, and `--review-api-key-env`
- `compile --help`: exit `0`; help text lists `--volume`, `--chapter`, and `--chapters`
- `continue --help`: exit `0`; help text shows the `run`, `sessions`, and `resume` subcommands

- [x] **Step 3: Run the full test suite**

Run:
`python -m pytest tests/unit tests/integration -q --tb=short -rfE`

Expected:
- full suite passes with all milestone 1-9 tests green

Observed:
- `261 passed in 76.57s`

- [x] **Step 4: Mark verification steps complete in this plan**

Record:
- the observed smoke-test results
- the observed full-suite result

- [ ] **Step 5: Commit**

```bash
git add docs/architecture/ARCHITECTURE.md meta/plans/2026-04-20-pizhi-milestone-9-v1-closure.md
git commit -m "docs: record milestone 9 verification state"
```
