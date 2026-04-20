# Pizhi Milestone 10 Delivery and Extension Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the planned ten-milestone roadmap by adding the first internal extension-agent contract for review and maintenance flows, then finishing the user-facing delivery surface with runbooks, recovery docs, and command-help alignment.

**Architecture:** Milestone 10 adds a minimal declarative `agents:` config section, a runtime registry/execution layer, and additive hook dispatch that appends isolated extension sections into existing review and maintenance reports without letting extensions own source-of-truth writes. The rest of the milestone focuses on repository-as-product delivery: README, runbooks, recovery guides, architecture closure, and contract tests that keep docs aligned with the CLI.

**Tech Stack:** Python 3.14, pytest, argparse, dataclasses, pathlib, existing provider execution/run store, existing review/maintenance services, Markdown documentation

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\milestone-10-delivery-and-extension`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -q --tb=short -rfE`
  - Observed while writing this plan: `264 passed in 84.31s`

## File Map

- `src/pizhi/core/config.py`: extend project config with an optional `agents:` section and strict validation helpers for extension-agent specs
- `src/pizhi/domain/agent_extensions.py`: define extension-agent domain objects such as `AgentSpec`, `AgentExecutionTarget`, and `AgentExecutionResult`
- `src/pizhi/services/agent_registry.py`: load enabled/disabled agents from config and resolve them by hook family and target scope
- `src/pizhi/services/agent_extensions.py`: execute declarative extension agents through a system-owned contract and normalize failures into structured results
- `src/pizhi/services/review_documents.py`: render additive extension sections for chapter notes and full review reports while preserving built-in sections
- `src/pizhi/services/ai_review_service.py`: expose reusable provider-backed review helpers if extension review execution can share prompt/result parsing machinery
- `src/pizhi/commands/review_cmd.py`: dispatch configured review extension agents after built-in structural and AI review paths, then render failure-isolated report sections
- `src/pizhi/services/maintenance.py`: dispatch configured maintenance extension agents after built-in deterministic maintenance and append their results into maintenance summaries
- `src/pizhi/cli.py`: align help text if milestone 10 changes command descriptions or surfaced workflow wording
- `docs/architecture/ARCHITECTURE.md`: update the architecture to describe the implemented v1 extension boundary instead of future intent
- `README.md`: add a top-level product overview and shortest-start guide if absent
- `docs/guides/getting-started.md`: add the main runbook from init through provider-backed writing/review/compile flows
- `docs/guides/recovery.md`: add failure-recovery guidance for provider failures, apply failures, continue resume, and review/maintenance retries
- `tests/unit/test_config.py`: cover `agents:` config round-trip and validation failures
- `tests/unit/test_agent_extensions.py`: cover domain parsing, registry behavior, execution normalization, and failure isolation
- `tests/unit/test_review_documents.py`: cover additive extension sections and malformed payload handling
- `tests/unit/test_maintenance.py`: cover maintenance summary/report integration with extension findings
- `tests/integration/test_review_command.py`: cover review extension execution and failure isolation at CLI level
- `tests/integration/test_cli_help_contract.py`: keep key `--help` output aligned with documented major workflows
- `tests/integration/test_docs_contract.py`: verify the delivered docs exist and mention the canonical command sequence used by the runbook
- `docs/superpowers/plans/2026-04-20-pizhi-milestone-10-delivery-and-extension.md`: update verification notes as tasks complete

### Task 1: Add Declarative Agent Config And Runtime Registry

**Files:**
- Modify: `src/pizhi/core/config.py`
- Create: `src/pizhi/domain/agent_extensions.py`
- Create: `src/pizhi/services/agent_registry.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/unit/test_agent_extensions.py`

- [ ] **Step 1: Write the failing config and registry tests**

```python
def test_config_round_trip_preserves_agent_specs(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)

    config = default_config(name="Test Novel")
    config.agents = [
        AgentSpec(
            agent_id="critique.chapter",
            kind="review",
            description="chapter critique agent",
            enabled=True,
            target_scope="chapter",
            prompt_template="Review the chapter for pacing drift.",
        ),
        AgentSpec(
            agent_id="archive.audit",
            kind="maintenance",
            description="archive audit agent",
            enabled=False,
            target_scope="project",
            prompt_template="Audit the maintenance summary for missed archive work.",
        ),
    ]
    save_config(path, config)

    loaded = load_config(path)
    assert loaded.agents is not None
    assert [agent.agent_id for agent in loaded.agents] == ["critique.chapter", "archive.audit"]
    assert loaded.agents[1].enabled is False


def test_load_config_rejects_unknown_agent_kind(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        '''
project: {name: Test, genre: "", pov: "", created: "2026-04-20", last_updated: "2026-04-20"}
chapters: {total_planned: 0, per_volume: 20}
generation:
  context_window: {prev_chapters: 2, max_outline_words: 500, max_chapter_words: 5000}
  style: {tone: "", dialogue_ratio: 0.35}
consistency: {auto_check: true, checkpoint_interval: 3}
foreshadowing: {auto_archive_resolved: true, reminder_threshold: 5}
agents:
  - agent_id: unsupported.audit
    kind: unknown
    description: bad
    enabled: true
    target_scope: project
    prompt_template: nope
'''.strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown agent kind"):
        load_config(path)


def test_agent_registry_filters_enabled_agents_by_kind_and_scope():
    registry = AgentRegistry(
        [
            AgentSpec(... kind="review", enabled=True, target_scope="chapter", ...),
            AgentSpec(... kind="review", enabled=False, target_scope="chapter", ...),
            AgentSpec(... kind="maintenance", enabled=True, target_scope="project", ...),
        ]
    )

    chapter_review_agents = registry.iter_enabled(kind="review", target_scope="chapter")

    assert [agent.agent_id for agent in chapter_review_agents] == ["critique.chapter"]
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_config.py tests/unit/test_agent_extensions.py -q --tb=short -rfE`

Expected:
- failures because `ProjectConfig` does not yet support `agents:` and the registry/domain modules do not exist

- [ ] **Step 3: Implement agent config parsing, validation, and registry lookup**

```python
@dataclass(slots=True)
class AgentSpec:
    agent_id: str
    kind: Literal["review", "maintenance"]
    description: str
    enabled: bool
    target_scope: Literal["chapter", "project"]
    prompt_template: str


@dataclass(slots=True)
class ProjectConfig:
    ...
    agents: list[AgentSpec] | None = None
```

```python
class AgentRegistry:
    def __init__(self, specs: Iterable[AgentSpec]):
        self._specs = list(specs)

    def iter_enabled(self, *, kind: str, target_scope: str) -> list[AgentSpec]:
        return [
            spec
            for spec in self._specs
            if spec.enabled and spec.kind == kind and spec.target_scope == target_scope
        ]
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_config.py tests/unit/test_agent_extensions.py -q --tb=short -rfE`

Expected: selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/core/config.py src/pizhi/domain/agent_extensions.py src/pizhi/services/agent_registry.py tests/unit/test_config.py tests/unit/test_agent_extensions.py
git commit -m "feat: add declarative agent registry"
```

### Task 2: Build Structured Extension Execution And Failure Isolation

**Files:**
- Modify: `src/pizhi/services/ai_review_service.py`
- Create: `src/pizhi/services/agent_extensions.py`
- Test: `tests/unit/test_agent_extensions.py`

- [ ] **Step 1: Write the failing extension-execution tests**

```python
def test_execute_agent_spec_normalizes_successful_issue_payload(monkeypatch, initialized_project):
    spec = AgentSpec(
        agent_id="critique.chapter",
        kind="review",
        description="chapter critique agent",
        enabled=True,
        target_scope="chapter",
        prompt_template="Review this chapter for pacing drift.",
    )

    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_prompt_request",
        lambda *args, **kwargs: FakeExecution(normalized_text="### 问题 1\n- **类别**：节奏\n..."),
    )

    result = execute_agent_spec(
        initialized_project,
        spec,
        target="ch002",
        context_markdown="context",
    )

    assert result.status == "succeeded"
    assert result.summary
    assert result.issues


def test_execute_agent_spec_converts_provider_failure_into_failed_result(monkeypatch, initialized_project):
    spec = AgentSpec(...)

    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_prompt_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider down")),
    )

    result = execute_agent_spec(initialized_project, spec, target="project", context_markdown="context")

    assert result.status == "failed"
    assert result.failure_reason == "provider down"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_agent_extensions.py -q --tb=short -rfE`

Expected:
- failures because extension execution helpers and normalized result objects do not exist yet

- [ ] **Step 3: Implement extension execution with structured normalization**

```python
@dataclass(frozen=True, slots=True)
class AgentExecutionResult:
    agent_id: str
    kind: str
    status: str
    summary: str
    issues: list[AIReviewIssue]
    suggestions: list[str]
    failure_reason: str | None
    run_id: str | None
```

```python
def execute_agent_spec(project_root: Path, spec: AgentSpec, *, target: str, context_markdown: str) -> AgentExecutionResult:
    prompt_request = PromptRequest(
        command_name=f"{spec.kind}-agent",
        prompt_text=render_agent_prompt(spec, target=target, context_markdown=context_markdown),
        metadata={"agent_id": spec.agent_id, "kind": spec.kind, "target": target},
        referenced_files=[],
    )
    try:
        execution = execute_prompt_request(project_root, prompt_request, target=target, route_name="review")
    except Exception as exc:
        return AgentExecutionResult.failed(spec, str(exc))
    return normalize_agent_execution(spec, execution)
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_agent_extensions.py -q --tb=short -rfE`

Expected: selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/ai_review_service.py src/pizhi/services/agent_extensions.py tests/unit/test_agent_extensions.py
git commit -m "feat: add structured extension execution"
```

### Task 3: Hook Review Flows And Render Additive Extension Sections

**Files:**
- Modify: `src/pizhi/commands/review_cmd.py`
- Modify: `src/pizhi/services/review_documents.py`
- Modify: `src/pizhi/services/agent_registry.py`
- Modify: `src/pizhi/services/agent_extensions.py`
- Test: `tests/unit/test_review_documents.py`
- Test: `tests/integration/test_review_command.py`

- [ ] **Step 1: Write the failing review-hook tests**

```python
def test_write_chapter_review_notes_appends_extension_sections(tmp_path):
    path = tmp_path / "notes.md"

    write_chapter_review_notes(
        path,
        author_notes="author",
        structural_markdown="- structural",
        ai_review_markdown="- ai",
        extension_sections=[
            ExtensionReportSection(agent_id="critique.chapter", title="Review Agent critique.chapter", body="- issue"),
        ],
    )

    text = path.read_text(encoding="utf-8")
    assert "## 作者备注" in text
    assert "## Review Agent critique.chapter" in text
    assert "- issue" in text


def test_review_command_execute_records_extension_failure_without_losing_builtin_sections(...):
    ...
    assert "## A 类结构检查" in notes_text
    assert "## B 类 AI 审查" in notes_text
    assert "## Review Agent critique.chapter" in notes_text
    assert "failed" in notes_text.lower()
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_review_documents.py tests/integration/test_review_command.py -q --tb=short -rfE`

Expected:
- failures because review documents and review command do not yet understand extension sections

- [ ] **Step 3: Implement review-agent dispatch and additive report rendering**

```python
registry = load_agent_registry(project_root)
review_agents = registry.iter_enabled(kind="review", target_scope="project" if args.full else "chapter")
extension_results = [
    execute_agent_spec(project_root, spec, target=target_name, context_markdown=context.prompt_context)
    for spec in review_agents
]
```

```python
def write_chapter_review_notes(..., extension_sections: list[ExtensionReportSection] | None = None) -> None:
    sections = {
        "作者备注": author_notes,
        "A 类结构检查": structural_markdown,
        "B 类 AI 审查": ai_review_markdown,
        **{section.title: section.body for section in extension_sections or []},
    }
    write_sectioned_markdown(path, sections, section_order=[...])
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_review_documents.py tests/integration/test_review_command.py -q --tb=short -rfE`

Expected: selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/commands/review_cmd.py src/pizhi/services/review_documents.py src/pizhi/services/agent_registry.py src/pizhi/services/agent_extensions.py tests/unit/test_review_documents.py tests/integration/test_review_command.py
git commit -m "feat: add review extension hooks"
```

### Task 4: Hook Maintenance Flows And Append Extension Findings

**Files:**
- Modify: `src/pizhi/services/maintenance.py`
- Modify: `src/pizhi/services/agent_registry.py`
- Modify: `src/pizhi/services/agent_extensions.py`
- Test: `tests/unit/test_maintenance.py`
- Test: `tests/integration/test_review_command.py`

- [ ] **Step 1: Write the failing maintenance-hook tests**

```python
def test_run_full_maintenance_appends_extension_findings(initialized_project, monkeypatch):
    configure_maintenance_agent(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.agent_extensions.execute_agent_spec",
        lambda *args, **kwargs: AgentExecutionResult(
            agent_id="archive.audit",
            kind="maintenance",
            status="succeeded",
            summary="archive summary",
            issues=[],
            suggestions=["rotate timeline archive"],
            failure_reason=None,
            run_id="run_123",
        ),
    )

    result = run_full_maintenance(initialized_project)

    assert any(finding.category == "Maintenance agent" for finding in result.findings)
    assert "archive.audit" in format_maintenance_summary(result)
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_maintenance.py tests/integration/test_review_command.py -q --tb=short -rfE`

Expected:
- failures because maintenance does not yet execute extension agents or render their findings

- [ ] **Step 3: Implement maintenance-agent dispatch and rendering**

```python
def _run_maintenance(project_root: Path) -> MaintenanceResult:
    ...
    registry = load_agent_registry(project_root)
    extension_results = [
        execute_agent_spec(project_root, spec, target="project", context_markdown=build_maintenance_context(...))
        for spec in registry.iter_enabled(kind="maintenance", target_scope="project")
    ]
    findings = _build_findings(synopsis_review, archive_result, extension_results)
```

```python
if extension_result.status == "succeeded":
    findings.append(MaintenanceFinding(category="Maintenance agent", detail=f"{agent_id}: {summary}"))
else:
    findings.append(MaintenanceFinding(category="Maintenance agent", detail=f"{agent_id}: failed - {failure_reason}"))
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_maintenance.py tests/integration/test_review_command.py -q --tb=short -rfE`

Expected: selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/maintenance.py src/pizhi/services/agent_registry.py src/pizhi/services/agent_extensions.py tests/unit/test_maintenance.py tests/integration/test_review_command.py
git commit -m "feat: add maintenance extension hooks"
```

### Task 5: Finish Delivery Docs, Help Contracts, And Architecture Closure

**Files:**
- Modify or Create: `README.md`
- Create: `docs/guides/getting-started.md`
- Create: `docs/guides/recovery.md`
- Modify: `docs/architecture/ARCHITECTURE.md`
- Modify: `src/pizhi/cli.py`
- Test: `tests/integration/test_cli_help_contract.py`
- Test: `tests/integration/test_docs_contract.py`
- Modify: `docs/superpowers/plans/2026-04-20-pizhi-milestone-10-delivery-and-extension.md`

- [ ] **Step 1: Write the failing documentation contract tests**

```python
def test_readme_and_runbook_exist_and_reference_canonical_flow(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    runbook = (project_root / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")

    assert "pizhi init" in readme
    assert "pizhi provider configure" in runbook
    assert "pizhi apply --run-id" in runbook
    assert "pizhi continue run --execute" in runbook
    assert "pizhi review --execute" in runbook


def test_cli_help_mentions_delivery_relevant_subcommands():
    parser = build_parser()
    help_text = parser.format_help()

    assert "provider" in help_text
    assert "apply" in help_text
    assert "continue" in help_text
    assert "review" in help_text
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_cli_help_contract.py tests/integration/test_docs_contract.py -q --tb=short -rfE`

Expected:
- failures because the new delivery docs and contract tests do not exist yet

- [ ] **Step 3: Implement documentation closure and help alignment**

```markdown
# Pizhi

Pizhi is a file-backed long-form fiction workflow that supports deterministic planning,
provider-backed generation, explicit apply, checkpointed continue sessions, structural review,
AI review, maintenance, and manuscript compilation.

## Quick Start

1. `python -m pizhi init --project-name "..."`
2. `python -m pizhi provider configure`
3. `python -m pizhi brainstorm --execute`
4. `python -m pizhi apply --run-id <run_id>`
...
```

```python
review_parser = subparsers.add_parser("review", help="run structural and optional AI consistency review")
compile_parser = subparsers.add_parser("compile", help="compile manuscript output by volume, chapter, or chapter range")
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/integration/test_cli_help_contract.py tests/integration/test_docs_contract.py -q --tb=short -rfE`

Expected: selected tests `PASSED`

- [ ] **Step 5: Run the full regression suite**

Run:
`python -m pytest tests/unit tests/integration -q --tb=short -rfE`

Expected: all tests `PASSED`

- [ ] **Step 6: Update plan verification notes and commit**

```bash
git add README.md docs/guides/getting-started.md docs/guides/recovery.md docs/architecture/ARCHITECTURE.md src/pizhi/cli.py tests/integration/test_cli_help_contract.py tests/integration/test_docs_contract.py docs/superpowers/plans/2026-04-20-pizhi-milestone-10-delivery-and-extension.md
git commit -m "docs: close delivery and extension milestone"
```

## Verification Checklist

- [ ] `agents:` config round-trips cleanly and rejects invalid kinds/scopes
- [ ] review extension agents append isolated sections without replacing built-in review output
- [ ] maintenance extension agents append findings without breaking deterministic maintenance behavior
- [ ] extension-agent failures are visible but do not corrupt notes or reports
- [ ] delivered docs cover init → provider configure → execute → apply → continue → review → compile
- [ ] architecture docs describe the implemented v1 extension boundary
- [ ] `python -m pytest tests/unit tests/integration -q --tb=short -rfE` passes
