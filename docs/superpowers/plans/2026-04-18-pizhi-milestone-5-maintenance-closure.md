# Pizhi Milestone 5 Maintenance Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the maintenance loop by fixing the remaining maintenance regressions, deterministically promoting valid `synopsis_candidate.md` files, rotating fixed 50-chapter archives, and wiring shared maintenance into `write`, `continue`, and `review --full`.

**Architecture:** Milestone 5 keeps the filesystem as the only truth source and extends the milestone 4 snapshot with timeline, archive-range, and tracked-foreshadowing views. New `synopsis_review`, `archive_service`, and `maintenance` services own deterministic maintenance logic, while write/review entry points only orchestrate them. Archive rotation remains conservative and idempotent: it never guesses missing metadata and never overwrites conflicting archive files.

**Tech Stack:** Python 3.14, pytest, pathlib, dataclasses, Markdown-style text parsing, JSONL chapter index storage

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\milestone-5-maintenance-closure`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -v`
  - Expected: current branch baseline passes cleanly in this worktree
  - Observed while writing this plan: `48 passed`

## File Map

- `src/pizhi/domain/project_state.py`: snapshot-level dataclasses, per-artifact archive metadata, maintenance-facing derived collections
- `src/pizhi/domain/foreshadowing.py`: tracker parsing/formatting, `Resolved In` / `Abandoned In` metadata, tracked section helpers
- `src/pizhi/domain/timeline.py`: live/archive timeline parsing helpers and major-turning-point extraction
- `src/pizhi/services/project_snapshot.py`: load timeline entries, sealed archive ranges, existing archive files, and tracked foreshadowing into one snapshot
- `src/pizhi/services/status_report.py`: align tracked foreshadowing windows with structural review
- `src/pizhi/services/consistency/structural.py`: restore single-chapter continuity checks and keep full-review checks aligned with snapshot rules
- `src/pizhi/services/synopsis_review.py`: deterministic synopsis-candidate parsing, coverage validation, promotion/preservation behavior, cache report output
- `src/pizhi/services/archive_service.py`: fixed-range archive computation, timeline/foreshadowing migration, idempotency/conflict detection
- `src/pizhi/services/maintenance.py`: post-write/full-review orchestration and maintenance result summaries
- `src/pizhi/services/chapter_writer.py`: stop leaving stale synopsis notes and persist `Resolved In: chNNN` metadata on resolved foreshadowing entries
- `src/pizhi/services/write_service.py`: trigger post-write maintenance when a response file is applied
- `src/pizhi/services/continue_service.py`: collect maintenance summaries and surface them at checkpoint time
- `src/pizhi/core/templates.py`: render checkpoint summaries with maintenance results
- `src/pizhi/commands/review_cmd.py`: run full maintenance, append maintenance summary to `review_full.md`, and print compact maintenance counts
- `tests/unit/test_status_report.py`: tracked-foreshadowing regression coverage
- `tests/unit/test_structural_review.py`: chapter continuity regression coverage
- `tests/unit/test_project_snapshot.py`: snapshot archive/timeline discovery coverage
- `tests/unit/test_foreshadowing.py`: close-chapter parsing/formatting coverage
- `tests/unit/test_synopsis_review.py`: candidate parsing, promotion, and failure-report coverage
- `tests/unit/test_archive_service.py`: fixed-range archive/idempotency/data-gap coverage
- `tests/integration/test_write_command.py`: valid/invalid synopsis maintenance integration
- `tests/integration/test_continue_command.py`: checkpoint maintenance summary integration
- `tests/integration/test_review_command.py`: `review --full` backfill archive + maintenance summary integration
- `tests/fixtures/chapter_outputs/ch001_response_synopsis_valid.md`: response fixture with valid synopsis coverage markers
- `tests/fixtures/chapter_outputs/ch001_response_synopsis_invalid.md`: response fixture with invalid/missing coverage markers

### Task 1: Restore Maintenance Parity Regressions

**Files:**
- Modify: `src/pizhi/services/status_report.py`
- Modify: `src/pizhi/services/consistency/structural.py`
- Test: `tests/unit/test_status_report.py`
- Test: `tests/unit/test_structural_review.py`

- [ ] **Step 1: Write the failing regression tests**

```python
def test_build_status_report_treats_referenced_entries_as_tracked(initialized_project):
    ...
    assert [entry.entry_id for entry in report.overdue_foreshadowing] == ["F900"]


def test_structural_review_single_chapter_flags_missing_previous_chapter(initialized_project):
    ...
    assert any(issue.category == "章节号连续性" for issue in report.chapter_issues[3])
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_status_report.py::test_build_status_report_treats_referenced_entries_as_tracked tests/unit/test_structural_review.py::test_structural_review_single_chapter_flags_missing_previous_chapter -v`

Expected:
- `status_report` test fails because only `Active` entries are tracked
- `structural_review` test fails because single-chapter review does not emit a continuity issue

- [ ] **Step 3: Implement the minimal regression fixes**

```python
TRACKED_SECTIONS = {"Active", "Referenced"}

tracked_entries = [
    entry for entry in snapshot.foreshadowing_entries if entry.section in TRACKED_SECTIONS
]
```

```python
if chapter_number > 1 and (chapter_number - 1) not in snapshot.chapters:
    issues.append(
        StructuralIssue(
            category="章节号连续性",
            severity="高",
            description=f"第 {chapter_number} 章之前缺少 ch{chapter_number - 1:03d}。",
            evidence=f"available chapters: {sorted(snapshot.chapters)}",
            suggestion="补回缺失章节，或修正错误的索引/目录状态。",
        )
    )
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_status_report.py::test_build_status_report_treats_referenced_entries_as_tracked tests/unit/test_structural_review.py::test_structural_review_single_chapter_flags_missing_previous_chapter -v`

Expected: both `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/status_report.py src/pizhi/services/consistency/structural.py tests/unit/test_status_report.py tests/unit/test_structural_review.py
git commit -m "fix: restore maintenance parity checks"
```

### Task 2: Extend Domain Contracts And Snapshot Inputs

**Files:**
- Modify: `src/pizhi/domain/project_state.py`
- Modify: `src/pizhi/domain/foreshadowing.py`
- Modify: `src/pizhi/domain/timeline.py`
- Modify: `src/pizhi/services/project_snapshot.py`
- Test: `tests/unit/test_foreshadowing.py`
- Test: `tests/unit/test_project_snapshot.py`

- [ ] **Step 1: Write the failing unit tests for close-chapter metadata and archive-aware snapshot fields**

```python
def test_parse_tracker_entries_reads_resolved_in_and_abandoned_in():
    entries = parse_tracker_entries(TRACKER_TEXT)
    assert entries[0].closed_in_chapter == 5
    assert entries[1].closed_in_chapter == 10


def test_load_project_snapshot_discovers_existing_archive_ranges(initialized_project):
    ...
    assert snapshot.existing_timeline_archive_ranges == [ArchiveRange(1, 50)]
    assert snapshot.existing_foreshadowing_archive_ranges == []
    assert [entry.entry_id for entry in snapshot.active_or_referenced_foreshadowing] == ["F001"]


def test_load_project_snapshot_includes_archived_major_turning_points(initialized_project):
    ...
    assert [entry.event_id for entry in snapshot.major_turning_points] == ["T001-01", "T060-02"]
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_foreshadowing.py::test_parse_tracker_entries_reads_resolved_in_and_abandoned_in tests/unit/test_project_snapshot.py::test_load_project_snapshot_discovers_existing_archive_ranges -v`

Expected:
- parser test fails because `ForeshadowingEntry` does not expose close-chapter metadata
- snapshot tests fail because `ProjectSnapshot` has no per-artifact archive fields and does not merge archived timeline turning points

- [ ] **Step 3: Implement the domain and snapshot extensions**

```python
@dataclass(frozen=True, slots=True)
class ArchiveRange:
    start_chapter: int
    end_chapter: int


@dataclass(frozen=True, slots=True)
class ForeshadowingEntry:
    ...
    closed_in_chapter: int | None
```

```python
return ProjectSnapshot(
    ...,
    timeline_entries=timeline_entries,
    active_or_referenced_foreshadowing=tracked_entries,
    major_turning_points=major_turning_points,
    eligible_archive_ranges=_sealed_ranges(latest_chapter),
    existing_timeline_archive_ranges=_discover_archive_ranges(paths.archive_dir, "timeline"),
    existing_foreshadowing_archive_ranges=_discover_archive_ranges(paths.archive_dir, "foreshadowing"),
)
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_foreshadowing.py tests/unit/test_project_snapshot.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/domain/project_state.py src/pizhi/domain/foreshadowing.py src/pizhi/domain/timeline.py src/pizhi/services/project_snapshot.py tests/unit/test_foreshadowing.py tests/unit/test_project_snapshot.py
git commit -m "feat: extend snapshot inputs for maintenance"
```

### Task 3: Add Deterministic Synopsis Review

**Files:**
- Create: `src/pizhi/services/synopsis_review.py`
- Modify: `src/pizhi/services/chapter_writer.py`
- Test: `tests/unit/test_synopsis_review.py`

- [ ] **Step 1: Write the failing synopsis review unit tests**

```python
def test_review_synopsis_candidate_promotes_valid_candidate(initialized_project):
    ...
    assert review_result.promoted is True
    assert not paths.synopsis_candidate_file.exists()


def test_review_synopsis_candidate_preserves_invalid_candidate(initialized_project):
    ...
    assert review_result.promoted is False
    assert paths.synopsis_candidate_file.exists()
    assert "missing foreshadowing ids" in review_text
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_synopsis_review.py -v`

Expected: FAIL with import error or missing promotion logic

- [ ] **Step 3: Implement synopsis parsing, validation, promotion, and stale-note cleanup**

```python
def review_synopsis_candidate(project_root: Path) -> SynopsisReviewResult:
    snapshot = load_project_snapshot(project_root)
    body, markers = parse_synopsis_candidate(paths.synopsis_candidate_file.read_text(...))
    missing_foreshadowing = sorted(required_foreshadowing - markers.foreshadowing_ids)
    missing_turning_points = sorted(required_turning_points - markers.major_turning_points)
    ...
```

```python
if parsed.metadata.synopsis_changed and parsed.sections.synopsis_new:
    _write_text(paths.synopsis_candidate_file, parsed.sections.synopsis_new + "\n")
    # Do not write the old placeholder note here; maintenance owns review outcomes.
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_synopsis_review.py -v`

Expected: all synopsis review tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/synopsis_review.py src/pizhi/services/chapter_writer.py tests/unit/test_synopsis_review.py
git commit -m "feat: add deterministic synopsis review"
```

### Task 4: Add Fixed-Range Archive Rotation

**Files:**
- Create: `src/pizhi/services/archive_service.py`
- Modify: `src/pizhi/domain/foreshadowing.py`
- Modify: `src/pizhi/services/chapter_writer.py`
- Test: `tests/unit/test_archive_service.py`

- [ ] **Step 1: Write the failing archive service tests**

```python
def test_archive_service_rotates_sealed_timeline_range(initialized_project):
    ...
    assert (paths.archive_dir / "timeline_ch001-050.md").exists()
    assert "## T001-01" not in paths.timeline_file.read_text(encoding="utf-8")


def test_archive_service_keeps_closed_foreshadowing_without_close_chapter_live(initialized_project):
    ...
    assert "F099" in paths.foreshadowing_file.read_text(encoding="utf-8")
    assert "missing close chapter" in result.findings[0].description
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/unit/test_archive_service.py -v`

Expected: FAIL because archive rotation and close-chapter formatting do not exist

- [ ] **Step 3: Implement archive rotation and resolved-entry metadata**

```python
for item in operations.get("resolved", []):
    sections["Resolved"] = _upsert_entry(
        sections["Resolved"],
        resolved_id,
        _format_resolved_entry(item, chapter_number),
    )
```

```python
def rotate_archives(project_root: Path) -> ArchiveResult:
    snapshot = load_project_snapshot(project_root)
    pending_timeline_ranges = [
        rng for rng in snapshot.eligible_archive_ranges if rng not in snapshot.existing_timeline_archive_ranges
    ]
    pending_foreshadowing_ranges = [
        rng for rng in snapshot.eligible_archive_ranges if rng not in snapshot.existing_foreshadowing_archive_ranges
    ]
    ...
```

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/unit/test_archive_service.py tests/unit/test_foreshadowing.py -v`

Expected: all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/archive_service.py src/pizhi/domain/foreshadowing.py src/pizhi/services/chapter_writer.py tests/unit/test_archive_service.py tests/unit/test_foreshadowing.py
git commit -m "feat: add fixed-range archive rotation"
```

### Task 5: Wire Shared Maintenance Into Write, Continue, And Full Review

**Files:**
- Create: `src/pizhi/services/maintenance.py`
- Modify: `src/pizhi/services/write_service.py`
- Modify: `src/pizhi/services/continue_service.py`
- Modify: `src/pizhi/core/templates.py`
- Modify: `src/pizhi/commands/review_cmd.py`
- Modify: `tests/integration/test_write_command.py`
- Modify: `tests/integration/test_continue_command.py`
- Modify: `tests/integration/test_review_command.py`
- Create: `tests/fixtures/chapter_outputs/ch001_response_synopsis_valid.md`
- Create: `tests/fixtures/chapter_outputs/ch001_response_synopsis_invalid.md`

- [ ] **Step 1: Write the failing integration tests**

```python
def test_write_command_promotes_valid_synopsis_candidate(initialized_project, fixture_text):
    ...
    assert (initialized_project / ".pizhi" / "global" / "synopsis.md").read_text(encoding="utf-8").startswith("# Synopsis")


def test_review_command_full_backfills_archive_and_reports_maintenance(initialized_project):
    ...
    assert "Maintenance findings:" in result.stdout
    assert (initialized_project / ".pizhi" / "archive" / "timeline_ch001-050.md").exists()


def test_continue_command_checkpoint_includes_maintenance_summary(initialized_project, fixture_text):
    ...
    assert "Maintenance" in checkpoint_text
    assert "Synopsis review" in checkpoint_text
```

- [ ] **Step 2: Run the targeted integration tests to verify they fail**

Run:
`python -m pytest tests/integration/test_write_command.py tests/integration/test_continue_command.py tests/integration/test_review_command.py -v`

Expected:
- write test fails because no maintenance hook promotes the candidate
- continue test fails because checkpoint summaries do not yet include maintenance output
- review test fails because full review does not backfill archive work or report maintenance

- [ ] **Step 3: Implement the orchestration layer and entry-point wiring**

```python
@dataclass(frozen=True, slots=True)
class MaintenanceResult:
    synopsis_review: SynopsisReviewResult | None
    archive_result: ArchiveResult | None
    findings: list[MaintenanceFinding]
```

```python
chapter_result = apply_chapter_response(...)
maintenance_result = run_after_write(self.project_root) if chapter_result is not None else None
return WriteResult(prompt_artifact=artifact, chapter_result=chapter_result, maintenance_result=maintenance_result)
```

```python
maintenance_result = run_full_maintenance(project_root)
report_text = format_structural_report(report) + format_maintenance_summary(maintenance_result)
```

- [ ] **Step 4: Run the targeted integration tests again**

Run:
`python -m pytest tests/integration/test_write_command.py tests/integration/test_continue_command.py tests/integration/test_review_command.py -v`

Expected: all selected integration tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/pizhi/services/maintenance.py src/pizhi/services/write_service.py src/pizhi/services/continue_service.py src/pizhi/core/templates.py src/pizhi/commands/review_cmd.py tests/integration/test_write_command.py tests/integration/test_continue_command.py tests/integration/test_review_command.py tests/fixtures/chapter_outputs/ch001_response_synopsis_valid.md tests/fixtures/chapter_outputs/ch001_response_synopsis_invalid.md
git commit -m "feat: wire maintenance into write and review flows"
```

### Task 6: Final Verification And Plan State Update

**Files:**
- Modify: `docs/superpowers/plans/2026-04-18-pizhi-milestone-5-maintenance-closure.md`

- [ ] **Step 1: Run command smoke tests**

Run:
- `python -m pizhi write --help`
- `python -m pizhi continue --help`
- `python -m pizhi review --help`

Expected: all commands exit `0`

- [ ] **Step 2: Run the full test suite**

Run:
`python -m pytest tests/unit tests/integration -v`

Expected: all tests `PASSED` and count increases beyond the 48-test baseline

- [ ] **Step 3: Mark verification steps complete in this plan**

Update this file so the executed verification boxes are checked and add the final observed command/test results near Task 6.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-18-pizhi-milestone-5-maintenance-closure.md
git commit -m "docs: record milestone 5 verification state"
```
