# Pizhi Milestone 2 Deterministic Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build Pizhi's deterministic chapter engine so captured AI chapter output can be parsed, persisted into `.pizhi/`, structurally reviewed, and compiled into `manuscript/`.

**Architecture:** Keep milestone 2 focused on deterministic file semantics. The implementation adds parser primitives for YAML frontmatter and named Markdown sections, then layers a chapter application service on top to write chapter files, update global trackers, and drive `compile` and `review`. AI-specific prompting and model orchestration remain out of scope until milestone 3.

**Tech Stack:** Python 3.11+, `argparse`, `pathlib`, `dataclasses`, `json`, `re`, `PyYAML`, `pytest`

---

## File Map

- Create: `src/pizhi/core/frontmatter.py`
- Create: `src/pizhi/core/markdown_sections.py`
- Create: `src/pizhi/domain/__init__.py`
- Create: `src/pizhi/domain/worldview.py`
- Create: `src/pizhi/domain/foreshadowing.py`
- Create: `src/pizhi/domain/timeline.py`
- Create: `src/pizhi/services/chapter_parser.py`
- Create: `src/pizhi/services/chapter_writer.py`
- Create: `src/pizhi/services/compiler.py`
- Create: `src/pizhi/services/consistency/__init__.py`
- Create: `src/pizhi/services/consistency/structural.py`
- Create: `src/pizhi/commands/compile_cmd.py`
- Create: `src/pizhi/commands/review_cmd.py`
- Create: `tests/fixtures/chapter_outputs/ch001_response.md`
- Create: `tests/fixtures/chapter_outputs/ch001_response_invalid_timeline.md`
- Create: `tests/fixtures/chapter_outputs/ch002_response.md`
- Create: `tests/unit/test_frontmatter.py`
- Create: `tests/unit/test_markdown_sections.py`
- Create: `tests/unit/test_chapter_parser.py`
- Create: `tests/unit/test_worldview.py`
- Create: `tests/unit/test_foreshadowing.py`
- Create: `tests/unit/test_timeline.py`
- Create: `tests/unit/test_structural_review.py`
- Create: `tests/integration/test_chapter_writer.py`
- Create: `tests/integration/test_compile_command.py`
- Create: `tests/integration/test_review_command.py`
- Modify: `src/pizhi/cli.py`
- Modify: `src/pizhi/core/paths.py`
- Modify: `tests/conftest.py`

### Planned Responsibilities

- `src/pizhi/core/frontmatter.py`: extract YAML frontmatter and validate that the document contains a well-formed metadata block.
- `src/pizhi/core/markdown_sections.py`: split the post-frontmatter Markdown into body plus named sections such as `characters_snapshot`, `relationships_snapshot`, `worldview_patch`, and `synopsis_new`.
- `src/pizhi/domain/worldview.py`: apply `Added`, `Modified`, and `Retracted` patch sections to the current `global/worldview.md` using exact bold-title matching.
- `src/pizhi/domain/foreshadowing.py`: update `global/foreshadowing.md` for introduced/referenced/resolved items while preserving the four lifecycle sections.
- `src/pizhi/domain/timeline.py`: append chapter timeline events and provide sortable event extraction for monotonicity checks.
- `src/pizhi/services/chapter_parser.py`: turn a raw AI chapter response into a structured parsed object with metadata, body, snapshots, optional patch blocks, and validation errors.
- `src/pizhi/services/chapter_writer.py`: persist a parsed chapter into chapter/global files, update `index.jsonl`, stage `synopsis_candidate.md`, and write `notes.md` when safe replacement is deferred.
- `src/pizhi/services/compiler.py`: group drafted/reviewed/compiled chapter texts by volume and emit `manuscript/vol_XX.md`.
- `src/pizhi/services/consistency/structural.py`: run A-class checks for file completeness, chapter continuity, foreshadowing legality, character mentions, and time monotonicity.
- `src/pizhi/commands/compile_cmd.py`: user-facing CLI for manuscript compilation.
- `src/pizhi/commands/review_cmd.py`: user-facing CLI for structural review of one chapter or the whole project.
- `tests/fixtures/chapter_outputs/*.md`: stable golden fixtures for valid and invalid chapter outputs.

### Task 1: Add parser primitives for frontmatter and named Markdown sections

**Files:**
- Create: `src/pizhi/core/frontmatter.py`
- Create: `src/pizhi/core/markdown_sections.py`
- Create: `tests/unit/test_frontmatter.py`
- Create: `tests/unit/test_markdown_sections.py`

- [x] **Step 1: Write failing unit tests for frontmatter extraction and section splitting**

```python
from pizhi.core.frontmatter import parse_frontmatter
from pizhi.core.markdown_sections import split_chapter_sections


def test_parse_frontmatter_returns_metadata_and_body():
    raw = "---\nchapter_title: Test\n---\nBody\n"
    metadata, body = parse_frontmatter(raw)

    assert metadata["chapter_title"] == "Test"
    assert body == "Body\n"


def test_split_chapter_sections_finds_required_named_blocks():
    raw = (
        "正文\n\n"
        "## characters_snapshot\n\n角色\n\n"
        "## relationships_snapshot\n\n关系\n"
    )
    sections = split_chapter_sections(raw)

    assert sections.body == "正文"
    assert sections.characters_snapshot == "角色"
    assert sections.relationships_snapshot == "关系"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_frontmatter.py tests/unit/test_markdown_sections.py -v`
Expected: FAIL because the parser primitive modules do not exist yet.

- [x] **Step 3: Write the minimal implementation**

```python
def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    ...


@dataclass(slots=True)
class ChapterSections:
    body: str
    characters_snapshot: str
    relationships_snapshot: str
    worldview_patch: str | None
    synopsis_new: str | None
```

Implement strict parsing rules:

- the document must start with a YAML frontmatter block delimited by `---`
- missing required `characters_snapshot` or `relationships_snapshot` sections is a hard error
- optional `worldview_patch` and `synopsis_new` sections may be absent

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_frontmatter.py tests/unit/test_markdown_sections.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/pizhi/core/frontmatter.py src/pizhi/core/markdown_sections.py tests/unit/test_frontmatter.py tests/unit/test_markdown_sections.py
git commit -m "feat: add chapter parser primitives"
```

### Task 2: Build the chapter parser and sample fixtures

**Files:**
- Create: `src/pizhi/services/chapter_parser.py`
- Create: `tests/fixtures/chapter_outputs/ch001_response.md`
- Create: `tests/fixtures/chapter_outputs/ch001_response_invalid_timeline.md`
- Create: `tests/fixtures/chapter_outputs/ch002_response.md`
- Create: `tests/unit/test_chapter_parser.py`

- [x] **Step 1: Write failing tests for parsing a full chapter response fixture**

```python
from pathlib import Path

from pizhi.services.chapter_parser import parse_chapter_response


def test_parse_chapter_response_fixture():
    raw = Path("tests/fixtures/chapter_outputs/ch001_response.md").read_text(encoding="utf-8")
    parsed = parse_chapter_response(raw)

    assert parsed.metadata.chapter_title == "第一章 雨夜访客"
    assert parsed.metadata.worldview_changed is True
    assert parsed.sections.worldview_patch is not None
    assert "沈轩" in parsed.sections.characters_snapshot
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_chapter_parser.py -v`
Expected: FAIL because the parser service and fixtures do not exist yet.

- [x] **Step 3: Write minimal fixtures and parser implementation**

```python
@dataclass(slots=True)
class ChapterMetadata:
    chapter_title: str
    word_count_estimated: int
    characters_involved: list[str]
    worldview_changed: bool
    synopsis_changed: bool
    timeline_events: list[dict[str, Any]]
    foreshadowing: dict[str, Any]
```

```python
@dataclass(slots=True)
class ParsedChapterResponse:
    metadata: ChapterMetadata
    sections: ChapterSections
```

Implement validation rules:

- `worldview_changed: true` requires a `worldview_patch` section
- `synopsis_changed: true` requires a `synopsis_new` section
- invalid or missing frontmatter keys raise a parser error rather than silently defaulting

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_chapter_parser.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/pizhi/services/chapter_parser.py tests/fixtures/chapter_outputs tests/unit/test_chapter_parser.py
git commit -m "feat: add chapter response parser"
```

### Task 3: Persist parsed chapters and update worldview, foreshadowing, and timeline

**Files:**
- Create: `src/pizhi/domain/__init__.py`
- Create: `src/pizhi/domain/worldview.py`
- Create: `src/pizhi/domain/foreshadowing.py`
- Create: `src/pizhi/domain/timeline.py`
- Create: `src/pizhi/services/chapter_writer.py`
- Modify: `src/pizhi/core/paths.py`
- Modify: `tests/conftest.py`
- Create: `tests/unit/test_worldview.py`
- Create: `tests/unit/test_foreshadowing.py`
- Create: `tests/unit/test_timeline.py`
- Create: `tests/integration/test_chapter_writer.py`

- [x] **Step 1: Write failing unit and integration tests for chapter application**

```python
from pathlib import Path

from pizhi.domain.worldview import apply_worldview_patch
from pizhi.services.chapter_writer import apply_chapter_response


def test_worldview_patch_modifies_existing_bold_title():
    current = "## 势力\n- **雷老板势力范围**：深水埗至旺角\n"
    patch = "## Modified\n- **雷老板势力范围**：深水埗至湾仔\n"

    updated = apply_worldview_patch(current, patch)
    assert "深水埗至湾仔" in updated


def test_apply_chapter_response_writes_chapter_and_updates_index(initialized_project):
    raw = Path("tests/fixtures/chapter_outputs/ch001_response.md").read_text(encoding="utf-8")
    result = apply_chapter_response(initialized_project, chapter_number=1, raw_response=raw)

    assert result.chapter_dir.joinpath("text.md").exists()
    assert result.chapter_dir.joinpath("characters.md").exists()
    assert result.chapter_dir.joinpath("relationships.md").exists()
    assert "drafted" in initialized_project.joinpath(".pizhi", "chapters", "index.jsonl").read_text(encoding="utf-8")
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_worldview.py tests/unit/test_foreshadowing.py tests/unit/test_timeline.py tests/integration/test_chapter_writer.py -v`
Expected: FAIL because the domain helpers and writer service do not exist yet.

- [x] **Step 3: Write minimal implementation**

```python
def apply_worldview_patch(current_text: str, patch_text: str) -> str:
    ...


def apply_chapter_response(project_root: Path, chapter_number: int, raw_response: str) -> ChapterWriteResult:
    ...
```

Implement the deterministic write rules:

- write chapter files under `.pizhi/chapters/chXXX/`
- update `index.jsonl` with `status="drafted"`, title, volume, summary, and update date
- append timeline events to `global/timeline.md`
- move foreshadowing items across sections in `global/foreshadowing.md`
- stage `global/synopsis_candidate.md` when `synopsis_changed` is true, but do not auto-replace `synopsis.md` yet; instead write a note explaining AI coverage review is still pending
- fail hard if a worldview `Modified` or `Retracted` title matches zero or multiple current entries

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_worldview.py tests/unit/test_foreshadowing.py tests/unit/test_timeline.py tests/integration/test_chapter_writer.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/pizhi/domain src/pizhi/services/chapter_writer.py src/pizhi/core/paths.py tests/conftest.py tests/unit/test_worldview.py tests/unit/test_foreshadowing.py tests/unit/test_timeline.py tests/integration/test_chapter_writer.py
git commit -m "feat: persist parsed chapter outputs"
```

### Task 4: Add manuscript compilation

**Files:**
- Create: `src/pizhi/services/compiler.py`
- Create: `src/pizhi/commands/compile_cmd.py`
- Modify: `src/pizhi/cli.py`
- Create: `tests/integration/test_compile_command.py`

- [x] **Step 1: Write a failing integration test for `pizhi compile`**

```python
from subprocess import run
import sys

from pizhi.services.chapter_writer import apply_chapter_response


def test_compile_command_writes_volume_file(initialized_project):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "compile"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (initialized_project / "manuscript" / "vol_01.md").exists()
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_compile_command.py -v`
Expected: FAIL because the command and service do not exist yet.

- [x] **Step 3: Write minimal implementation**

```python
def compile_manuscript(project_root: Path) -> list[Path]:
    ...
```

Compilation rules for milestone 2:

- read chapter records from `index.jsonl`
- include chapters with status `drafted`, `reviewed`, or `compiled`
- group by `vol`, order by chapter number, and concatenate `text.md`
- write `manuscript/vol_XX.md`
- update included chapter records to `compiled`

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_compile_command.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/pizhi/services/compiler.py src/pizhi/commands/compile_cmd.py src/pizhi/cli.py tests/integration/test_compile_command.py
git commit -m "feat: add manuscript compilation"
```

### Task 5: Add structural review and notes output

**Files:**
- Create: `src/pizhi/services/consistency/__init__.py`
- Create: `src/pizhi/services/consistency/structural.py`
- Create: `src/pizhi/commands/review_cmd.py`
- Modify: `src/pizhi/cli.py`
- Create: `tests/unit/test_structural_review.py`
- Create: `tests/integration/test_review_command.py`

- [x] **Step 1: Write failing tests for structural review**

```python
from pizhi.services.consistency.structural import run_structural_review


def test_structural_review_flags_non_monotonic_timeline(initialized_project):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    report = run_structural_review(initialized_project, chapter_number=2)
    assert report.issues
    assert report.issues[0].category == "时间线单调性"
```

```python
def test_review_command_writes_notes_file(initialized_project):
    ...
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_structural_review.py tests/integration/test_review_command.py -v`
Expected: FAIL because the structural review module and CLI command do not exist yet.

- [x] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class StructuralIssue:
    category: str
    severity: str
    description: str
    evidence: str
    suggestion: str
```

```python
def run_structural_review(project_root: Path, chapter_number: int | None = None, full: bool = False) -> StructuralReport:
    ...
```

Implement A-class checks from the architecture:

- file completeness for `text.md`, `characters.md`, `relationships.md`
- chapter continuity against existing `index.jsonl`
- foreshadowing resolved IDs must already exist in active or referenced sections
- character names from `characters_involved` must appear in chapter text
- non-flashback timeline events cannot move backward relative to the previous chapter's last non-flashback event

Write issues to `chXXX/notes.md` using the documented notes format. `review --full` should aggregate all chapter issues but may skip AI-only semantics.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_structural_review.py tests/integration/test_review_command.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/pizhi/services/consistency src/pizhi/commands/review_cmd.py src/pizhi/cli.py tests/unit/test_structural_review.py tests/integration/test_review_command.py
git commit -m "feat: add structural consistency review"
```

### Task 6: Run milestone 2 verification and update the plan

**Files:**
- Modify: `meta/plans/2026-04-16-pizhi-milestone-2-engine.md`

- [x] **Step 1: Run the full milestone 2 test suite**

Run: `python -m pytest tests/unit tests/integration -v`
Expected: PASS

- [x] **Step 2: Run CLI smoke checks for the new commands**

Run:

```bash
python -m pizhi compile --help
python -m pizhi review --help
```

Expected: both commands exit with code 0 and show the expected options.

- [x] **Step 3: Mark completed steps in this plan**

Update the checkbox states in this file so the plan remains truthful after execution.

- [x] **Step 4: Commit**

```bash
git add meta/plans/2026-04-16-pizhi-milestone-2-engine.md
git commit -m "docs: record milestone 2 verification state"
```

