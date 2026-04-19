# Pizhi Milestone 8 AI Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add provider-backed B-class AI review for `review --chapter` and `review --full`, with partitioned review documents, review-specific provider overrides, and preserved deterministic review behavior.

**Architecture:** Milestone 8 keeps A-class structural review as the first stage, then layers bounded AI review context assembly, provider-backed semantic review execution, and partitioned document writing on top. `notes.md` and `review_full.md` become stable sectioned documents so machine-managed review output can coexist with human-authored notes.

**Tech Stack:** Python 3.14, pytest, argparse, pathlib, dataclasses, stdlib `re`/`json`, existing provider execution and run store, existing structural review and project snapshot services

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\milestone-8-ai-review`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -v`
  - Observed while writing this plan: `191 passed`

## File Map

- `src/pizhi/core/config.py`: extend provider config with review-specific override fields and fallback loading support
- `src/pizhi/commands/provider_cmd.py`: support configuring review-specific provider settings in both interactive and flag-driven modes
- `src/pizhi/services/provider_execution.py`: allow review execution to use explicit provider override values while reusing run artifact persistence
- `src/pizhi/domain/ai_review.py`: define semantic review issue dataclasses, enums, and structured Markdown parsing/validation
- `src/pizhi/services/review_documents.py`: read and write partitioned `notes.md` and `review_full.md` while preserving human-authored sections
- `src/pizhi/services/ai_review_context.py`: build chapter-level and full-review AI context packets from chapters, globals, snapshot data, and A-class findings
- `src/pizhi/services/ai_review_service.py`: build AI review prompts, execute provider-backed review calls, validate structured output, and surface failures
- `src/pizhi/services/consistency/structural.py`: stop owning whole-file `notes.md` rewrites and expose A-class data to the new document writer
- `src/pizhi/commands/review_cmd.py`: orchestrate A-class review, maintenance, optional AI review, partitioned document writing, and CLI summaries
- `src/pizhi/cli.py`: add `--execute` to `review` without regressing existing syntax
- `tests/unit/test_config.py`: cover review-provider config round-trip and fallback behavior
- `tests/integration/test_provider_configure_command.py`: cover interactive and flag-driven review override configuration
- `tests/unit/test_ai_review.py`: cover semantic issue parsing, enum validation, and malformed output rejection
- `tests/unit/test_review_documents.py`: cover partitioned `notes.md` and `review_full.md` writing/preservation behavior
- `tests/unit/test_ai_review_context.py`: cover chapter and full-review context assembly
- `tests/unit/test_ai_review_service.py`: cover prompt execution, run artifact persistence, success parsing, and failure modes
- `tests/unit/test_structural_review.py`: update expectations for A-class notes writing responsibilities if needed
- `tests/integration/test_review_command.py`: cover chapter/full `--execute` behavior and failure semantics
- `docs/superpowers/plans/2026-04-19-pizhi-milestone-8-ai-review.md`: mark verification results after execution

### Task 1: Add Review Provider Override Configuration

**Files:**
- Modify: `src/pizhi/core/config.py`
- Modify: `src/pizhi/commands/provider_cmd.py`
- Modify: `src/pizhi/services/provider_execution.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/integration/test_provider_configure_command.py`

- [ ] **Step 1: Write the failing config and CLI tests**

```python
def test_config_round_trip_includes_review_provider_override(tmp_path):
    config = default_config("Pizhi")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        review_model="gpt-5.4-mini",
        review_base_url="https://api.openai.com/v1",
        review_api_key_env="OPENAI_REVIEW_API_KEY",
    )
    save_config(tmp_path / "config.yaml", config)

    loaded = load_config(tmp_path / "config.yaml")
    assert loaded.provider.review_model == "gpt-5.4-mini"
    assert loaded.provider.review_api_key_env == "OPENAI_REVIEW_API_KEY"


def test_provider_configure_command_writes_review_override_fields(initialized_project):
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
            "--review-model",
            "gpt-5.4-mini",
            "--review-api-key-env",
            "OPENAI_REVIEW_API_KEY",
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    loaded = load_config(initialized_project / ".pizhi" / "config.yaml")
    assert loaded.provider.review_model == "gpt-5.4-mini"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_config.py tests/integration/test_provider_configure_command.py -v`

Expected:
- failures because review override fields and CLI flags do not exist yet

- [ ] **Step 3: Implement review override config and fallback support**

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

    def resolve_review_config(self) -> ProviderSection:
        return ProviderSection(
            provider=self.provider,
            model=self.review_model or self.model,
            base_url=self.review_base_url or self.base_url,
            api_key_env=self.review_api_key_env or self.api_key_env,
        )
```

```python
provider_configure_parser.add_argument("--review-model", help="review model name")
provider_configure_parser.add_argument("--review-base-url", help="review base URL")
provider_configure_parser.add_argument("--review-api-key-env", help="environment variable for the review API key")
```

```python
provider_section = ProviderSection(
    provider=...,
    model=...,
    base_url=...,
    api_key_env=...,
    review_model=args.review_model or existing.review_model,
    review_base_url=args.review_base_url or existing.review_base_url,
    review_api_key_env=args.review_api_key_env or existing.review_api_key_env,
)
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_config.py tests/integration/test_provider_configure_command.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/core/config.py src/pizhi/commands/provider_cmd.py src/pizhi/services/provider_execution.py tests/unit/test_config.py tests/integration/test_provider_configure_command.py
git commit -m "feat: add review provider override configuration"
```

### Task 2: Add Semantic Review Domain And Partitioned Review Documents

**Files:**
- Create: `src/pizhi/domain/ai_review.py`
- Create: `src/pizhi/services/review_documents.py`
- Modify: `src/pizhi/services/consistency/structural.py`
- Test: `tests/unit/test_ai_review.py`
- Test: `tests/unit/test_review_documents.py`

- [ ] **Step 1: Write the failing parser and document tests**

```python
def test_parse_ai_review_markdown_returns_valid_issue_blocks():
    raw = """
### 问题 1
- **类别**：人物一致性
- **严重度**：高
- **描述**：沈轩前后动机冲突。
- **证据**：ch010 表示他要隐瞒，ch011 却直接摊牌。
- **建议修法**：改成试探式对话。
"""

    issues = parse_ai_review_issues(raw)
    assert issues[0].category == "人物一致性"
    assert issues[0].severity == "高"


def test_parse_ai_review_markdown_rejects_unknown_category():
    with pytest.raises(ValueError, match="unknown review category"):
        parse_ai_review_issues("### 问题 1\n- **类别**：风格问题\n...")


def test_write_chapter_review_notes_preserves_author_notes(tmp_path):
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "## 作者备注\n\n手工备注。\n\n## A 类结构检查\n\n旧内容\n",
        encoding="utf-8",
        newline="\n",
    )

    write_chapter_review_notes(
        notes_path,
        author_notes=None,
        structural_markdown="A",
        ai_review_markdown="B",
    )

    raw = notes_path.read_text(encoding="utf-8")
    assert "手工备注" in raw
    assert "## B 类 AI 审查" in raw
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_ai_review.py tests/unit/test_review_documents.py -v`

Expected:
- import errors because the semantic review domain and review document writer do not exist yet

- [ ] **Step 3: Implement semantic issue parsing and partitioned document writing**

```python
@dataclass(frozen=True, slots=True)
class AIReviewIssue:
    category: str
    severity: str
    description: str
    evidence: str
    suggestion: str
```

```python
ALLOWED_REVIEW_CATEGORIES = {
    "人物一致性",
    "时间线合理性",
    "世界设定一致性",
    "因果一致性",
    "资源一致性",
    "Synopsis 覆盖性",
}

ALLOWED_REVIEW_SEVERITIES = {"高", "中", "低"}
```

```python
def write_chapter_review_notes(path: Path, *, structural_markdown: str, ai_review_markdown: str) -> None:
    sections = load_sectioned_markdown(path, required=["作者备注", "A 类结构检查", "B 类 AI 审查"])
    sections["A 类结构检查"] = structural_markdown
    sections["B 类 AI 审查"] = ai_review_markdown
    write_sectioned_markdown(path, sections, section_order=["作者备注", "A 类结构检查", "B 类 AI 审查"])
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_ai_review.py tests/unit/test_review_documents.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/domain/ai_review.py src/pizhi/services/review_documents.py src/pizhi/services/consistency/structural.py tests/unit/test_ai_review.py tests/unit/test_review_documents.py
git commit -m "feat: add semantic review parsing and partitioned review documents"
```

### Task 3: Build Chapter And Full AI Review Context Assembly

**Files:**
- Create: `src/pizhi/services/ai_review_context.py`
- Test: `tests/unit/test_ai_review_context.py`

- [ ] **Step 1: Write the failing context assembly tests**

```python
def test_build_chapter_ai_review_context_includes_target_previous_and_globals(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    report = run_structural_review(initialized_project, chapter_number=2)

    context = build_chapter_ai_review_context(initialized_project, 2, report.chapter_issues[2])

    assert "当前章节正文" in context.prompt_context
    assert "上一章正文" in context.prompt_context
    assert "世界观" in context.prompt_context
    assert "A 类结构问题" in context.prompt_context


def test_build_full_ai_review_context_compresses_project_snapshot(initialized_project, fixture_text):
    ...
    context = build_full_ai_review_context(initialized_project, structural_report, maintenance_result)
    assert "活跃伏笔" in context.prompt_context
    assert "重大转折" in context.prompt_context
    assert "Maintenance" in context.prompt_context
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_ai_review_context.py -v`

Expected:
- import errors because the AI review context builder does not exist yet

- [ ] **Step 3: Implement bounded chapter and full-review context builders**

```python
@dataclass(frozen=True, slots=True)
class AIReviewContext:
    scope: str
    target: str
    prompt_context: str
    referenced_files: list[str]
    metadata: dict[str, object]
```

```python
def build_chapter_ai_review_context(project_root: Path, chapter_number: int, structural_issues: list[StructuralIssue]) -> AIReviewContext:
    return AIReviewContext(
        scope="chapter",
        target=f"ch{chapter_number:03d}",
        prompt_context=_render_chapter_review_packet(...),
        referenced_files=[...],
        metadata={"chapter": chapter_number, "scope": "chapter_review"},
    )
```

```python
def build_full_ai_review_context(project_root: Path, report: StructuralReport, maintenance_result: MaintenanceResult) -> AIReviewContext:
    snapshot = load_project_snapshot(project_root)
    return AIReviewContext(
        scope="full",
        target="project",
        prompt_context=_render_full_review_packet(snapshot, report, maintenance_result),
        referenced_files=[...],
        metadata={"scope": "full_review"},
    )
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_ai_review_context.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/ai_review_context.py tests/unit/test_ai_review_context.py
git commit -m "feat: add ai review context assembly"
```

### Task 4: Add Provider-Backed AI Review Service

**Files:**
- Create: `src/pizhi/services/ai_review_service.py`
- Modify: `src/pizhi/services/provider_execution.py`
- Test: `tests/unit/test_ai_review_service.py`

- [ ] **Step 1: Write the failing AI review service tests**

```python
def test_run_ai_review_executes_with_review_provider_override(initialized_project, monkeypatch):
    context = AIReviewContext(scope="chapter", target="ch002", prompt_context="...", referenced_files=[], metadata={})
    _configure_provider_with_review_override(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "secret")
    monkeypatch.setattr("pizhi.services.provider_execution.build_provider_adapter", lambda *_: StubAdapter(VALID_AI_REVIEW_RESPONSE))

    result = run_ai_review(initialized_project, context)

    assert result.run_id.startswith("run-")
    assert result.record.metadata["model"] == "gpt-5.4-mini"
    assert result.issues[0].category == "人物一致性"


def test_run_ai_review_returns_failure_when_schema_is_invalid(initialized_project, monkeypatch):
    ...
    assert result.status == "failed"
    assert "unknown review category" in result.error_message
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_ai_review_service.py -v`

Expected:
- import errors because the AI review service does not exist yet

- [ ] **Step 3: Implement review prompt execution, parsing, and failure normalization**

```python
@dataclass(frozen=True, slots=True)
class AIReviewResult:
    status: str
    run_id: str | None
    issues: list[AIReviewIssue]
    rendered_markdown: str
    error_message: str | None
```

```python
def run_ai_review(project_root: Path, context: AIReviewContext) -> AIReviewResult:
    request = PromptRequest(
        command_name="review",
        prompt_text=build_ai_review_prompt(context),
        metadata=context.metadata,
        referenced_files=context.referenced_files,
    )
    execution = execute_prompt_request(
        project_root,
        request,
        target=context.target,
        provider_config=_load_review_provider_config(project_root),
    )
    if execution.status != "succeeded":
        return AIReviewResult(status="failed", run_id=execution.run_id, issues=[], rendered_markdown="", error_message=_failure_message(execution))
    issues = parse_ai_review_issues(execution.record.normalized_path.read_text(encoding="utf-8"))
    return AIReviewResult(status="succeeded", run_id=execution.run_id, issues=issues, rendered_markdown=format_ai_review_issues(issues), error_message=None)
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_ai_review_service.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/ai_review_service.py src/pizhi/services/provider_execution.py tests/unit/test_ai_review_service.py
git commit -m "feat: add provider-backed ai review service"
```

### Task 5: Wire `review --execute` For Chapter And Full Review

**Files:**
- Modify: `src/pizhi/cli.py`
- Modify: `src/pizhi/commands/review_cmd.py`
- Modify: `tests/integration/test_review_command.py`

- [ ] **Step 1: Write the failing integration tests for chapter/full execute flow**

```python
def test_review_command_chapter_execute_writes_partitioned_notes_and_run_id(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "review", "--chapter", "2", "--execute"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    notes_path = initialized_project / ".pizhi" / "chapters" / "ch002" / "notes.md"
    assert result.returncode == 0
    assert "Run ID:" in result.stdout
    assert "## A 类结构检查" in notes_path.read_text(encoding="utf-8")
    assert "## B 类 AI 审查" in notes_path.read_text(encoding="utf-8")


def test_review_command_full_execute_writes_partitioned_report(initialized_project, fixture_text):
    ...
    result = run([sys.executable, "-m", "pizhi", "review", "--full", "--execute"], ...)
    report_path = initialized_project / ".pizhi" / "cache" / "review_full.md"
    assert "## Maintenance" in report_path.read_text(encoding="utf-8")
    assert "## B 类 AI 审查" in report_path.read_text(encoding="utf-8")


def test_review_command_execute_preserves_a_class_output_when_ai_review_fails(initialized_project, fixture_text):
    ...
    assert result.returncode != 0
    assert "## A 类结构检查" in notes_path.read_text(encoding="utf-8")
    assert "AI 审查执行失败" in notes_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_review_command.py -v`

Expected:
- CLI failures because `review --execute` and partitioned outputs are not wired yet

- [ ] **Step 3: Implement chapter/full review execute orchestration**

```python
review_parser.add_argument("--execute", action="store_true", help="call the configured review provider")
```

```python
def run_review(args: argparse.Namespace) -> int:
    structural_report = run_structural_review(project_root, chapter_number=args.chapter, full=args.full)
    maintenance_result = run_full_maintenance(project_root) if args.full else None

    if args.full:
        write_full_review_document(...)
    else:
        write_chapter_review_notes(...)

    if not args.execute:
        return 0

    ai_context = build_full_ai_review_context(...) if args.full else build_chapter_ai_review_context(...)
    ai_result = run_ai_review(project_root, ai_context)
    update_review_documents_with_ai_result(...)
    return 0 if ai_result.status == "succeeded" else 1
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/integration/test_review_command.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/cli.py src/pizhi/commands/review_cmd.py tests/integration/test_review_command.py
git commit -m "feat: add ai review execution flow"
```

### Task 6: Final Verification And Plan State Update

**Files:**
- Modify: `docs/superpowers/plans/2026-04-19-pizhi-milestone-8-ai-review.md`

- [x] **Step 1: Run review command smoke tests**

Run:
- `python -m pizhi review --help`
- `python -m pizhi review --chapter 1 --execute --help`
- `python -m pizhi provider configure --help`

Observed: all three commands exited `0`. `review --help` and `review --chapter 1 --execute --help` both printed the `--execute` flag, and `provider configure --help` showed the review override options.

- [x] **Step 2: Run the full test suite**

Run:
`python -m pytest tests/unit tests/integration -v`

Observed: `228 passed in 68.91s`, which is above the 191-test baseline.

- [x] **Step 3: Mark verification steps complete in this plan**

Updated this file so the executed verification boxes are checked and recorded the observed smoke-test and full-suite results above.

- [x] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-19-pizhi-milestone-8-ai-review.md
git commit -m "docs: record milestone 8 verification state"
```

Committed as `b27af23`.
