# Pizhi Milestone 1 Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable slice of Pizhi: a Python CLI repository that can initialize a novel project and report project status from `.pizhi/` data.

**Architecture:** Keep the CLI thin and move filesystem logic into focused services and core helpers. Milestone 1 only covers deterministic bootstrap behavior: repository layout, templates, config/index persistence, `pizhi init`, and `pizhi status`. AI orchestration commands remain out of scope until the storage layer is proven by tests.

**Tech Stack:** Python 3.11+, `argparse`, `pathlib`, `dataclasses`, `json`, `PyYAML`, `pytest`

---

## File Map

- Create: `pyproject.toml`
- Create: `src/pizhi/__init__.py`
- Create: `src/pizhi/__main__.py`
- Create: `src/pizhi/cli.py`
- Create: `src/pizhi/commands/__init__.py`
- Create: `src/pizhi/commands/init_cmd.py`
- Create: `src/pizhi/commands/status_cmd.py`
- Create: `src/pizhi/core/__init__.py`
- Create: `src/pizhi/core/config.py`
- Create: `src/pizhi/core/jsonl_store.py`
- Create: `src/pizhi/core/paths.py`
- Create: `src/pizhi/core/templates.py`
- Create: `src/pizhi/services/__init__.py`
- Create: `src/pizhi/services/project_init.py`
- Create: `src/pizhi/services/status_report.py`
- Create: `tests/conftest.py`
- Create: `tests/integration/test_init_command.py`
- Create: `tests/integration/test_status_command.py`
- Create: `tests/unit/test_config.py`
- Create: `tests/unit/test_jsonl_store.py`
- Create: `tests/unit/test_status_report.py`
- Create: `docs/architecture/ARCHITECTURE.md`
- Modify: `ARCHITECTURE.md`

### Planned Responsibilities

- `pyproject.toml`: package metadata, console script, dev/test dependency setup
- `src/pizhi/cli.py`: argument parser and command dispatch
- `src/pizhi/commands/*.py`: user-facing command handlers only
- `src/pizhi/core/paths.py`: canonical project path resolution for `.pizhi/`, `global/`, `chapters/`, `manuscript/`
- `src/pizhi/core/config.py`: config dataclasses plus YAML load/save helpers
- `src/pizhi/core/jsonl_store.py`: append/read/update helpers for chapter index JSONL records
- `src/pizhi/core/templates.py`: starter file content for `config.yaml`, hooks, cache files, and Markdown placeholders
- `src/pizhi/services/project_init.py`: create the on-disk project layout used by `pizhi init`
- `src/pizhi/services/status_report.py`: compute counts, current chapter, next action, and compile state for `pizhi status`
- `tests/integration/*`: CLI behavior and generated file tree checks
- `tests/unit/*`: pure logic for config, JSONL, and status calculations

### Task 1: Scaffold the Python package and test harness

**Files:**
- Create: `pyproject.toml`
- Create: `src/pizhi/__init__.py`
- Create: `src/pizhi/__main__.py`
- Create: `src/pizhi/cli.py`
- Create: `src/pizhi/commands/__init__.py`
- Create: `src/pizhi/commands/init_cmd.py`
- Create: `src/pizhi/commands/status_cmd.py`
- Create: `src/pizhi/core/__init__.py`
- Create: `src/pizhi/services/__init__.py`
- Test: `tests/integration/test_init_command.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
from subprocess import run
import sys


def test_cli_shows_top_level_help(project_root):
    result = run(
        [sys.executable, "-m", "pizhi", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "init" in result.stdout
    assert "status" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_init_command.py::test_cli_shows_top_level_help -v`
Expected: FAIL with import or module-not-found errors because the package entrypoint does not exist yet.

- [ ] **Step 3: Write minimal package and parser implementation**

```python
# src/pizhi/__main__.py
from .cli import main

raise SystemExit(main())
```

```python
# src/pizhi/cli.py
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pizhi")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("init")
    subparsers.add_parser("status")
    return parser
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_init_command.py::test_cli_shows_top_level_help -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/pizhi tests/integration/test_init_command.py
git commit -m "feat: scaffold pizhi cli package"
```

### Task 2: Implement project path helpers, config I/O, and chapter index store

**Files:**
- Create: `src/pizhi/core/paths.py`
- Create: `src/pizhi/core/config.py`
- Create: `src/pizhi/core/jsonl_store.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/unit/test_jsonl_store.py`

- [ ] **Step 1: Write failing unit tests for config round-trip and JSONL updates**

```python
from pizhi.core.config import default_config, load_config, save_config
from pizhi.core.jsonl_store import ChapterIndexStore


def test_config_round_trip(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)
    save_config(path, default_config(name="Test Novel"))

    loaded = load_config(path)
    assert loaded.project.name == "Test Novel"


def test_chapter_index_store_upserts_record(tmp_path):
    store = ChapterIndexStore(tmp_path / "index.jsonl")
    store.upsert({"n": 1, "title": "雨夜访客", "vol": 1, "status": "outlined", "summary": "", "updated": "2026-04-15"})
    store.upsert({"n": 1, "title": "雨夜访客", "vol": 1, "status": "drafted", "summary": "摘要", "updated": "2026-04-16"})

    assert store.read_all()[0]["status"] == "drafted"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_config.py tests/unit/test_jsonl_store.py -v`
Expected: FAIL because the modules do not exist yet.

- [ ] **Step 3: Write the minimal data-layer implementation**

```python
@dataclass(slots=True)
class ProjectConfig:
    project: ProjectSection
    chapters: ChaptersSection
    generation: GenerationSection
    consistency: ConsistencySection
    foreshadowing: ForeshadowingSection
```

```python
class ChapterIndexStore:
    def read_all(self) -> list[dict]:
        ...

    def upsert(self, record: dict) -> None:
        ...
```

Implement `default_config(...)`, YAML serialization, path helpers for project roots, and deterministic JSONL upsert by chapter number.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_config.py tests/unit/test_jsonl_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/core tests/unit/test_config.py tests/unit/test_jsonl_store.py
git commit -m "feat: add config and chapter index primitives"
```

### Task 3: Implement project templates and `pizhi init`

**Files:**
- Create: `src/pizhi/core/templates.py`
- Create: `src/pizhi/services/project_init.py`
- Modify: `src/pizhi/commands/init_cmd.py`
- Modify: `src/pizhi/cli.py`
- Test: `tests/integration/test_init_command.py`

- [ ] **Step 1: Extend integration test to assert the generated project tree**

```python
def test_init_creates_expected_project_tree(project_root):
    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "init",
            "--project-name",
            "测试小说",
            "--genre",
            "港综商战",
            "--total-chapters",
            "260",
            "--per-volume",
            "20",
            "--pov",
            "第三人称有限视角",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (project_root / ".pizhi" / "config.yaml").exists()
    assert (project_root / ".pizhi" / "global" / "synopsis.md").exists()
    assert (project_root / ".pizhi" / "chapters" / "index.jsonl").exists()
    assert (project_root / "manuscript").is_dir()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_init_command.py::test_init_creates_expected_project_tree -v`
Expected: FAIL because `init` has no implementation.

- [ ] **Step 3: Write minimal implementation**

```python
def run_init(args: argparse.Namespace) -> int:
    service = ProjectInitService(Path.cwd())
    service.initialize(
        name=args.project_name,
        genre=args.genre,
        total_chapters=args.total_chapters,
        per_volume=args.per_volume,
        pov=args.pov,
    )
    return 0
```

Implement template helpers so `pizhi init` creates:

- `.pizhi/config.yaml`
- `.pizhi/global/{synopsis,worldview,timeline,foreshadowing,characters_index,outline_global,rules}.md`
- `.pizhi/chapters/index.jsonl`
- `.pizhi/chapters/ch000/{characters,relationships}.md`
- `.pizhi/hooks/{pre_chapter,post_chapter,consistency_check}.md`
- `.pizhi/cache/{last_session,pending_actions}.md`
- `.pizhi/archive/`
- `manuscript/`

- [ ] **Step 4: Run integration tests to verify they pass**

Run: `python -m pytest tests/integration/test_init_command.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/core/templates.py src/pizhi/services/project_init.py src/pizhi/commands/init_cmd.py src/pizhi/cli.py tests/integration/test_init_command.py
git commit -m "feat: add project initialization command"
```

### Task 4: Implement status calculation and `pizhi status`

**Files:**
- Create: `src/pizhi/services/status_report.py`
- Modify: `src/pizhi/commands/status_cmd.py`
- Modify: `src/pizhi/cli.py`
- Test: `tests/unit/test_status_report.py`
- Test: `tests/integration/test_status_command.py`

- [ ] **Step 1: Write failing tests for status reporting**

```python
from pizhi.services.status_report import build_status_report


def test_build_status_report_for_initialized_project(initialized_project):
    report = build_status_report(initialized_project)
    assert report.total_planned == 260
    assert report.chapter_counts["planned"] == 0
    assert report.next_chapter == 1
```

```python
def test_status_command_prints_summary(initialized_project):
    result = run(
        [sys.executable, "-m", "pizhi", "status"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Total planned chapters: 260" in result.stdout
    assert "Next chapter: ch001" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_status_report.py tests/integration/test_status_command.py -v`
Expected: FAIL because status logic is not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class StatusReport:
    total_planned: int
    per_volume: int
    chapter_counts: dict[str, int]
    latest_chapter: int | None
    next_chapter: int
```

```python
def build_status_report(project_root: Path) -> StatusReport:
    config = load_config(...)
    index_records = ChapterIndexStore(...).read_all()
    ...
```

Include graceful handling for:

- initialized projects with zero chapter records
- partially initialized projects missing optional files
- status counts grouped by `planned`, `outlined`, `drafted`, `reviewed`, `compiled`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_status_report.py tests/integration/test_status_command.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/status_report.py src/pizhi/commands/status_cmd.py src/pizhi/cli.py tests/unit/test_status_report.py tests/integration/test_status_command.py
git commit -m "feat: add project status reporting"
```

### Task 5: Move the architecture document into the docs tree and preserve discoverability

**Files:**
- Create: `docs/architecture/ARCHITECTURE.md`
- Modify: `ARCHITECTURE.md`
- Test: none

- [ ] **Step 1: Move the architecture doc into its final docs location**

Copy the current repository-root `ARCHITECTURE.md` into `docs/architecture/ARCHITECTURE.md` without content changes.

- [ ] **Step 2: Replace the root file with a short pointer**

```markdown
# Architecture Pointer

The canonical architecture document lives at `docs/architecture/ARCHITECTURE.md`.
```

- [ ] **Step 3: Verify the files manually**

Run: `git diff -- docs/architecture/ARCHITECTURE.md ARCHITECTURE.md`
Expected: the docs copy contains the full original content and the root file becomes a short pointer.

- [ ] **Step 4: Commit**

```bash
git add docs/architecture/ARCHITECTURE.md ARCHITECTURE.md
git commit -m "docs: move architecture into docs tree"
```

### Task 6: Run the milestone verification suite

**Files:**
- Modify: `docs/superpowers/plans/2026-04-15-pizhi-milestone-1-bootstrap.md`

- [ ] **Step 1: Run the full milestone 1 test suite**

Run: `python -m pytest tests/unit tests/integration -v`
Expected: PASS

- [ ] **Step 2: Run CLI smoke checks manually**

Run:

```bash
python -m pizhi --help
python -m pizhi init --help
python -m pizhi status --help
```

Expected: all commands exit with code 0 and show the expected options.

- [ ] **Step 3: Mark completed tasks in this plan**

Update the checkbox states in this file for any completed steps so the plan stays truthful.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-15-pizhi-milestone-1-bootstrap.md
git commit -m "docs: record milestone 1 verification state"
```
