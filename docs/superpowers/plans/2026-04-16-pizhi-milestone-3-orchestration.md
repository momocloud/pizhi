# Pizhi Milestone 3 Prompt-Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Pizhi's prompt-oriented orchestration layer so `brainstorm`, `outline expand`, `write`, and `continue` can assemble context, generate prompt packets, and persist user-supplied AI responses through the milestone 2 engine.

**Architecture:** Milestone 3 adds an adapter boundary without binding the project to a hosted model provider. Commands build typed prompt requests, the prompt-only adapter writes reusable prompt packets into `.pizhi/cache/`, and command-specific services optionally consume structured response files to update project state. `continue` composes `outline expand` and `write` flows and emits checkpoint summaries every three written chapters.

**Tech Stack:** Python 3.11+, `argparse`, `pathlib`, `dataclasses`, `json`, `re`, `PyYAML`, `pytest`

---

## File Map

- Create: `src/pizhi/adapters/__init__.py`
- Create: `src/pizhi/adapters/base.py`
- Create: `src/pizhi/adapters/prompt_only.py`
- Create: `src/pizhi/services/chapter_context.py`
- Create: `src/pizhi/services/brainstorm_service.py`
- Create: `src/pizhi/services/outline_service.py`
- Create: `src/pizhi/services/write_service.py`
- Create: `src/pizhi/services/continue_service.py`
- Create: `src/pizhi/commands/brainstorm_cmd.py`
- Create: `src/pizhi/commands/outline_cmd.py`
- Create: `src/pizhi/commands/write_cmd.py`
- Create: `src/pizhi/commands/continue_cmd.py`
- Create: `tests/fixtures/orchestration/brainstorm_response.md`
- Create: `tests/fixtures/orchestration/outline_expand_response.md`
- Create: `tests/unit/test_prompt_only_adapter.py`
- Create: `tests/unit/test_chapter_context.py`
- Create: `tests/unit/test_outline_service.py`
- Create: `tests/integration/test_brainstorm_command.py`
- Create: `tests/integration/test_outline_expand_command.py`
- Create: `tests/integration/test_write_command.py`
- Create: `tests/integration/test_continue_command.py`
- Modify: `src/pizhi/cli.py`
- Modify: `src/pizhi/core/paths.py`
- Modify: `src/pizhi/core/templates.py`
- Modify: `tests/conftest.py`

### Planned Responsibilities

- `src/pizhi/adapters/base.py`: typed prompt request/result models and a stable adapter interface.
- `src/pizhi/adapters/prompt_only.py`: write prompt packets to `.pizhi/cache/prompts/` plus a JSON manifest that records command name, target chapters, and referenced files.
- `src/pizhi/services/chapter_context.py`: assemble the Chapter Loop input bundle from global files, current outline, recent chapters, and chapter-index lookups.
- `src/pizhi/services/brainstorm_service.py`: build brainstorm prompts and apply a structured brainstorm response into `global/` and `ch000/`.
- `src/pizhi/services/outline_service.py`: build outline-expansion prompts, parse outline response blocks, write `outline.md` files, and upsert chapter index records to `outlined`.
- `src/pizhi/services/write_service.py`: build chapter-writing prompts and route response files through `chapter_writer`.
- `src/pizhi/services/continue_service.py`: orchestrate batch outline/write flows, consume response directories, and emit checkpoint summaries every three written chapters.
- `src/pizhi/commands/*.py`: thin CLI bindings only.

### Task 1: Add the prompt adapter boundary and prompt packet persistence

**Files:**
- Create: `src/pizhi/adapters/__init__.py`
- Create: `src/pizhi/adapters/base.py`
- Create: `src/pizhi/adapters/prompt_only.py`
- Modify: `src/pizhi/core/paths.py`
- Create: `tests/unit/test_prompt_only_adapter.py`

- [ ] **Step 1: Write the failing adapter test**

```python
from pizhi.adapters.base import PromptRequest
from pizhi.adapters.prompt_only import PromptOnlyAdapter


def test_prompt_only_adapter_writes_prompt_packet(initialized_project):
    adapter = PromptOnlyAdapter(initialized_project)
    request = PromptRequest(
        command_name="write",
        prompt_text="Write chapter 1",
        metadata={"chapter": 1},
        referenced_files=[".pizhi/global/synopsis.md"],
    )

    result = adapter.prepare(request)

    assert result.prompt_path.exists()
    assert result.manifest_path.exists()
    assert "Write chapter 1" in result.prompt_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_prompt_only_adapter.py -v`
Expected: FAIL because the adapter modules do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class PromptRequest:
    command_name: str
    prompt_text: str
    metadata: dict[str, Any]
    referenced_files: list[str]
```

```python
class PromptOnlyAdapter:
    def prepare(self, request: PromptRequest) -> PromptArtifact:
        ...
```

Persist prompt packets under `.pizhi/cache/prompts/` with:

- one Markdown prompt file
- one JSON manifest
- file names prefixed by command name and timestamp or sequence id

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_prompt_only_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/adapters src/pizhi/core/paths.py tests/unit/test_prompt_only_adapter.py
git commit -m "feat: add prompt-only adapter"
```

### Task 2: Add brainstorm prompt generation and structured response application

**Files:**
- Create: `src/pizhi/services/brainstorm_service.py`
- Create: `src/pizhi/commands/brainstorm_cmd.py`
- Create: `tests/fixtures/orchestration/brainstorm_response.md`
- Create: `tests/integration/test_brainstorm_command.py`
- Modify: `src/pizhi/cli.py`

- [ ] **Step 1: Write the failing brainstorm integration test**

```python
from subprocess import run
import sys


def test_brainstorm_command_applies_response_file(initialized_project):
    response_file = initialized_project / "brainstorm_response.md"
    response_file.write_text(fixture_text("brainstorm_response.md"), encoding="utf-8")

    result = run(
        [sys.executable, "-m", "pizhi", "brainstorm", "--response-file", str(response_file)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "故事总体简介" in (initialized_project / ".pizhi" / "global" / "synopsis.md").read_text(encoding="utf-8")
    assert "沈轩" in (initialized_project / ".pizhi" / "chapters" / "ch000" / "characters.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_brainstorm_command.py -v`
Expected: FAIL because the command and service do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Use a structured brainstorm response file with these sections:

```markdown
## synopsis
...
## worldview
...
## rules
...
## foreshadowing
...
## outline_global
...
## characters
...
## relationships
...
```

Implementation responsibilities:

- always generate a prompt packet through the prompt-only adapter
- when `--response-file` is provided, parse the sections and write them into `global/` plus `ch000/`
- update `cache/last_session.md` with brainstorm completion state

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_brainstorm_command.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/brainstorm_service.py src/pizhi/commands/brainstorm_cmd.py src/pizhi/cli.py tests/fixtures/orchestration/brainstorm_response.md tests/integration/test_brainstorm_command.py
git commit -m "feat: add brainstorm orchestration command"
```

### Task 3: Add outline expansion orchestration and outline persistence

**Files:**
- Create: `src/pizhi/services/outline_service.py`
- Create: `src/pizhi/commands/outline_cmd.py`
- Create: `tests/fixtures/orchestration/outline_expand_response.md`
- Create: `tests/unit/test_outline_service.py`
- Create: `tests/integration/test_outline_expand_command.py`
- Modify: `src/pizhi/cli.py`

- [ ] **Step 1: Write failing tests for outline response parsing and command application**

```python
from pizhi.services.outline_service import parse_outline_response


def test_parse_outline_response_returns_chapter_blocks(fixture_text):
    parsed = parse_outline_response(fixture_text("outline_expand_response.md"))
    assert parsed[0].chapter_number == 1
    assert parsed[0].title == "雨夜访客"
```

```python
def test_outline_expand_command_writes_outline_files(initialized_project):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_outline_service.py tests/integration/test_outline_expand_command.py -v`
Expected: FAIL because the service and command do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Use an outline response format like:

```markdown
## ch001 | 雨夜访客
...

## ch002 | 码头血衣
...
```

Implementation responsibilities:

- add CLI shape `pizhi outline expand`
- accept `--chapters START-END` and optional `--direction`
- generate a prompt packet through the adapter
- when `--response-file` is provided, write `.pizhi/chapters/chXXX/outline.md`
- update `index.jsonl` records to `outlined`
- append or refresh human-readable summaries in `global/outline_global.md`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_outline_service.py tests/integration/test_outline_expand_command.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/outline_service.py src/pizhi/commands/outline_cmd.py src/pizhi/cli.py tests/fixtures/orchestration/outline_expand_response.md tests/unit/test_outline_service.py tests/integration/test_outline_expand_command.py
git commit -m "feat: add outline expansion orchestration"
```

### Task 4: Add Chapter Loop context assembly and the `write` command

**Files:**
- Create: `src/pizhi/services/chapter_context.py`
- Create: `src/pizhi/services/write_service.py`
- Create: `src/pizhi/commands/write_cmd.py`
- Create: `tests/unit/test_chapter_context.py`
- Create: `tests/integration/test_write_command.py`
- Modify: `src/pizhi/cli.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write failing tests for chapter context assembly and write command**

```python
from pizhi.services.chapter_context import build_chapter_context


def test_build_chapter_context_includes_previous_chapter_artifacts(initialized_project, fixture_text):
    ...
    context = build_chapter_context(initialized_project, chapter_number=2)
    assert "synopsis" in context.required_inputs
    assert "previous_text" in context.required_inputs
    assert "current_outline" in context.required_inputs
```

```python
def test_write_command_applies_response_file(initialized_project):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_chapter_context.py tests/integration/test_write_command.py -v`
Expected: FAIL because the context service and command do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implementation responsibilities:

- build the deterministic Chapter Loop input bundle from synopsis, worldview, rules, foreshadowing, current outline, previous chapter text/characters/relationships, and optional second-previous chapter text when available
- generate a prompt packet through the adapter
- add CLI `pizhi write --chapter N [--response-file PATH]`
- when `--response-file` is supplied, pass it to `chapter_writer.apply_chapter_response`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_chapter_context.py tests/integration/test_write_command.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/chapter_context.py src/pizhi/services/write_service.py src/pizhi/commands/write_cmd.py src/pizhi/cli.py tests/unit/test_chapter_context.py tests/integration/test_write_command.py tests/conftest.py
git commit -m "feat: add chapter writing orchestration"
```

### Task 5: Add the `continue` workflow and checkpoint summaries

**Files:**
- Create: `src/pizhi/services/continue_service.py`
- Create: `src/pizhi/commands/continue_cmd.py`
- Create: `tests/integration/test_continue_command.py`
- Modify: `src/pizhi/core/templates.py`
- Modify: `src/pizhi/cli.py`

- [ ] **Step 1: Write failing integration tests for batch continuation**

```python
def test_continue_command_writes_checkpoint_summary_every_three_chapters(initialized_project):
    ...
```

The test should:

- prepare outline response and chapter response files for three chapters
- run `pizhi continue --count 3 --outline-response-file ... --chapter-responses-dir ...`
- assert that a checkpoint summary file exists under `.pizhi/cache/`
- assert that the summary mentions new chapter titles and foreshadowing changes

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_continue_command.py -v`
Expected: FAIL because the continue workflow and command do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implementation responsibilities:

- determine the next unwritten chapter range from `index.jsonl`
- build and save the outline prompt packet
- when outline and chapter response inputs are provided, apply them sequentially through the milestone 2 services
- after every three written chapters, emit a checkpoint summary under `.pizhi/cache/` listing:
  - chapter titles and 100-character summaries
  - relationship or character state changes using written snapshots
  - introduced and resolved foreshadowing IDs from chapter metadata

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_continue_command.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/continue_service.py src/pizhi/commands/continue_cmd.py src/pizhi/core/templates.py src/pizhi/cli.py tests/integration/test_continue_command.py
git commit -m "feat: add continue workflow checkpoints"
```

### Task 6: Run milestone 3 verification and update the plan

**Files:**
- Modify: `docs/superpowers/plans/2026-04-16-pizhi-milestone-3-orchestration.md`

- [ ] **Step 1: Run the full milestone 3 test suite**

Run: `python -m pytest tests/unit tests/integration -v`
Expected: PASS

- [ ] **Step 2: Run CLI smoke checks for the new commands**

Run:

```bash
python -m pizhi brainstorm --help
python -m pizhi outline --help
python -m pizhi write --help
python -m pizhi continue --help
```

Expected: all commands exit with code 0 and show the expected options.

- [ ] **Step 3: Mark completed steps in this plan**

Update the checkbox states in this file so the plan remains truthful after execution.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-16-pizhi-milestone-3-orchestration.md
git commit -m "docs: record milestone 3 verification state"
```
