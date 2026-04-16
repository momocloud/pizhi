# Pizhi Milestone 4 Maintenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified project snapshot layer and refactor `status` plus `review --full` to use it for whole-project maintenance reporting.

**Architecture:** Milestone 4 keeps the filesystem as the only write-path truth and adds a read-only `ProjectSnapshot` assembled from config, chapter index records, global Markdown trackers, per-chapter metadata, and artifact presence checks. `status` and structural review consume that shared snapshot so later archive, synopsis-candidate, and AI-review work can extend one read boundary instead of duplicating file-walking logic.

**Tech Stack:** Python 3.11+, `argparse`, `pathlib`, `dataclasses`, `json`, `re`, `PyYAML`, `pytest`

---

## File Map

- Create: `src/pizhi/domain/project_state.py`
- Create: `src/pizhi/services/project_snapshot.py`
- Create: `tests/unit/test_project_snapshot.py`
- Modify: `src/pizhi/domain/foreshadowing.py`
- Modify: `src/pizhi/services/status_report.py`
- Modify: `src/pizhi/services/consistency/structural.py`
- Modify: `src/pizhi/commands/status_cmd.py`
- Modify: `src/pizhi/commands/review_cmd.py`
- Modify: `tests/unit/test_foreshadowing.py`
- Modify: `tests/unit/test_status_report.py`
- Modify: `tests/unit/test_structural_review.py`
- Modify: `tests/integration/test_status_command.py`
- Modify: `tests/integration/test_review_command.py`
- Modify: `docs/superpowers/plans/2026-04-16-pizhi-milestone-4-maintenance.md`

### Planned Responsibilities

- `src/pizhi/domain/project_state.py`: read-model dataclasses for chapters, chapter artifacts, foreshadowing entries, pending chapter queues, and the assembled `ProjectSnapshot`.
- `src/pizhi/services/project_snapshot.py`: load config, `index.jsonl`, global trackers, chapter metadata, and artifact presence into a normalized snapshot with derived fields.
- `src/pizhi/domain/foreshadowing.py`: keep tracker update helpers and add full entry parsing plus `planned_payoff` normalization.
- `src/pizhi/services/status_report.py`: derive the maintenance dashboard from `ProjectSnapshot` instead of scanning files ad hoc.
- `src/pizhi/services/consistency/structural.py`: run chapter-level and project-level structural checks from the shared snapshot and write full-review summaries into `.pizhi/cache/review_full.md`.
- `src/pizhi/commands/status_cmd.py` and `src/pizhi/commands/review_cmd.py`: keep CLI bindings thin while exposing the expanded report output cleanly.

### Task 1: Add the project snapshot read model and loader

**Files:**
- Create: `src/pizhi/domain/project_state.py`
- Create: `src/pizhi/services/project_snapshot.py`
- Create: `tests/unit/test_project_snapshot.py`

- [ ] **Step 1: Write the failing project snapshot tests**

```python
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.project_snapshot import load_project_snapshot


def test_load_project_snapshot_for_initialized_project(initialized_project):
    snapshot = load_project_snapshot(initialized_project)

    assert snapshot.project_name == "Test Novel"
    assert snapshot.latest_chapter is None
    assert snapshot.next_chapter == 1
    assert snapshot.chapters == {}
```

```python
def test_load_project_snapshot_tracks_chapter_artifacts(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    snapshot = load_project_snapshot(initialized_project)

    assert snapshot.latest_chapter == 1
    assert snapshot.chapters[1].artifacts.text_exists is True
    assert snapshot.chapters[1].artifacts.meta_exists is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_project_snapshot.py -v`
Expected: FAIL because the snapshot loader and domain model do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class ChapterArtifacts:
    text_exists: bool
    characters_exists: bool
    relationships_exists: bool
    meta_exists: bool
```

```python
@dataclass(slots=True)
class ProjectSnapshot:
    project_name: str
    total_planned: int
    per_volume: int
    chapters: dict[int, ChapterState]
    latest_chapter: int | None
    next_chapter: int
```

Implementation responsibilities:

- load config with graceful fallback to `default_config`
- read `index.jsonl` when present
- load chapter directories referenced by index records
- capture artifact presence for `text.md`, `characters.md`, `relationships.md`, and `meta.json`
- compute `latest_chapter`, `next_chapter`, and sorted recent chapter state

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_project_snapshot.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/domain/project_state.py src/pizhi/services/project_snapshot.py tests/unit/test_project_snapshot.py
git commit -m "feat: add project snapshot loader"
```

### Task 2: Extend foreshadowing parsing and wire payoff normalization into the snapshot

**Files:**
- Modify: `src/pizhi/domain/foreshadowing.py`
- Modify: `src/pizhi/services/project_snapshot.py`
- Modify: `tests/unit/test_foreshadowing.py`
- Modify: `tests/unit/test_project_snapshot.py`

- [ ] **Step 1: Write the failing foreshadowing parsing tests**

```python
from pizhi.domain.foreshadowing import parse_planned_payoff
from pizhi.domain.foreshadowing import parse_tracker_entries


def test_parse_planned_payoff_range():
    payoff = parse_planned_payoff("ch010-ch015")
    assert payoff.start_chapter == 10
    assert payoff.end_chapter == 15
    assert payoff.open_ended is False
```

```python
def test_parse_tracker_entries_returns_active_entry():
    text = """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 码头血衣的来源
- **Planned Payoff**: ch005
- **Related Characters**: 沈轩

## Referenced

## Resolved

## Abandoned
"""

    entries = parse_tracker_entries(text)

    assert entries[0].entry_id == "F001"
    assert entries[0].section == "Active"
    assert entries[0].planned_payoff.start_chapter == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_foreshadowing.py tests/unit/test_project_snapshot.py -v`
Expected: FAIL because the tracker parser and payoff normalization helpers do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class PlannedPayoff:
    start_chapter: int | None
    end_chapter: int | None
    open_ended: bool
```

```python
def parse_planned_payoff(value: str) -> PlannedPayoff:
    ...


def parse_tracker_entries(current_text: str) -> list[ForeshadowingTrackerEntry]:
    ...
```

Implementation responsibilities:

- parse `ch018`, `ch010-ch015`, and `ch030+`
- parse full tracker entries from all four sections, not just IDs
- preserve compatibility with the existing tracker update behavior
- load parsed foreshadowing entries into `ProjectSnapshot`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_foreshadowing.py tests/unit/test_project_snapshot.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/domain/foreshadowing.py src/pizhi/services/project_snapshot.py tests/unit/test_foreshadowing.py tests/unit/test_project_snapshot.py
git commit -m "feat: normalize foreshadowing payoff windows"
```

### Task 3: Refactor `status` to the project snapshot and add the maintenance dashboard

**Files:**
- Modify: `src/pizhi/services/status_report.py`
- Modify: `src/pizhi/commands/status_cmd.py`
- Modify: `tests/unit/test_status_report.py`
- Modify: `tests/integration/test_status_command.py`

- [ ] **Step 1: Write the failing status tests**

```python
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.status_report import build_status_report


def test_build_status_report_includes_pending_queues_and_foreshadowing(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    report = build_status_report(initialized_project)

    assert report.recent_chapters[0].number == 1
    assert report.pending_chapters["drafted"][0].number == 1
    assert report.active_foreshadowing_count >= 1
```

```python
def test_status_command_prints_dashboard_sections(initialized_project, fixture_text):
    ...
    assert "Recent chapters:" in result.stdout
    assert "Foreshadowing:" in result.stdout
    assert "Pending chapters:" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_status_report.py tests/integration/test_status_command.py -v`
Expected: FAIL because the report and CLI do not expose the new dashboard fields yet.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class StatusReport:
    project_name: str
    total_planned: int
    per_volume: int
    chapter_counts: dict[str, int]
    latest_chapter: int | None
    next_chapter: int
    compiled_volumes: int
    recent_chapters: list[RecentChapter]
    pending_chapters: dict[str, list[PendingChapter]]
    active_foreshadowing_count: int
```

Implementation responsibilities:

- derive the report from `load_project_snapshot`
- group pending chapters by lifecycle backlog:
  - outlined but not drafted
  - drafted but not reviewed
  - reviewed but not compiled
- expose near-payoff and overdue foreshadowing summaries
- print the dashboard in four sections without breaking partially initialized projects

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_status_report.py tests/integration/test_status_command.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/status_report.py src/pizhi/commands/status_cmd.py tests/unit/test_status_report.py tests/integration/test_status_command.py
git commit -m "feat: add maintenance status dashboard"
```

### Task 4: Refactor structural review to the project snapshot and add `review --full`

**Files:**
- Modify: `src/pizhi/services/consistency/structural.py`
- Modify: `src/pizhi/commands/review_cmd.py`
- Modify: `tests/unit/test_structural_review.py`
- Modify: `tests/integration/test_review_command.py`

- [ ] **Step 1: Write the failing full-review tests**

```python
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.consistency.structural import run_structural_review


def test_structural_review_full_flags_overdue_foreshadowing(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 6, fixture_text("ch001_response.md"))

    report = run_structural_review(initialized_project, full=True)

    assert report.global_issues
    assert any(issue.category == "伏笔超期" for issue in report.global_issues)
```

```python
def test_review_command_full_writes_cache_report(initialized_project, fixture_text):
    ...
    assert (initialized_project / ".pizhi" / "cache" / "review_full.md").exists()
    assert "Global issues:" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_structural_review.py tests/integration/test_review_command.py -v`
Expected: FAIL because the report still exposes a flat issue list and full review does not write a global report.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class StructuralReport:
    reviewed_chapters: list[int]
    chapter_issues: dict[int, list[StructuralIssue]]
    global_issues: list[StructuralIssue]
    stats: dict[str, int]
```

Implementation responsibilities:

- drive chapter checks from `ProjectSnapshot`
- preserve chapter-scoped `notes.md` output for single-chapter and full-review chapter findings
- add project-level findings for:
  - chapter index or directory mismatches
  - advanced chapter states missing required artifacts
  - obvious chapter-number gaps
  - overdue active or referenced foreshadowing
- write `.pizhi/cache/review_full.md` during `full=True`
- keep CLI output compact by printing summary counts instead of every issue line

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_structural_review.py tests/integration/test_review_command.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/consistency/structural.py src/pizhi/commands/review_cmd.py tests/unit/test_structural_review.py tests/integration/test_review_command.py
git commit -m "feat: add full structural review dashboard"
```

### Task 5: Run milestone 4 verification and update the plan

**Files:**
- Modify: `docs/superpowers/plans/2026-04-16-pizhi-milestone-4-maintenance.md`

- [ ] **Step 1: Run the full milestone 4 test suite**

Run: `python -m pytest tests/unit tests/integration -v`
Expected: PASS

- [ ] **Step 2: Run CLI smoke checks for the maintenance commands**

Run:

```bash
python -m pizhi status --help
python -m pizhi review --help
python -m pizhi review --full
```

Expected:

- both help commands exit with code 0
- `review --full` exits with code 0 in a test project and writes `.pizhi/cache/review_full.md`

- [ ] **Step 3: Mark completed steps in this plan**

Update the checkbox states in this file so the plan remains truthful after execution.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-16-pizhi-milestone-4-maintenance.md
git commit -m "docs: record milestone 4 verification state"
```
