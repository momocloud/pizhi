# Pizhi Milestone 4 Maintenance Design

## Goal

Build the first project-wide read model for Pizhi so maintenance-facing commands can reason about the novel as a whole instead of re-parsing individual files ad hoc.

This milestone delivers two user-facing upgrades:

- `pizhi review --full` becomes a deterministic whole-project structural audit
- `pizhi status` becomes an operational dashboard instead of a basic counter dump

## Scope

- Add a unified read-only project snapshot layer over the existing file-system truth sources
- Refactor `status` and structural review to consume that snapshot
- Extend foreshadowing parsing so status and review can reason about payoff windows
- Add tests around the snapshot, derived views, and CLI output

## Non-Goals

- Archive rotation
- `synopsis_candidate.md` validation and replacement
- AI semantic review
- Provider-backed model adapters
- New write-path storage formats

## Primary Decision

Milestone 4 uses a shared project snapshot instead of adding more command-specific readers.

The repository already has stable write-paths:

- `.pizhi/chapters/index.jsonl`
- `.pizhi/global/*.md`
- `.pizhi/chapters/chXXX/meta.json`
- chapter artifact files such as `text.md`, `characters.md`, and `relationships.md`

Those remain the only truth sources. The new layer is read-only and exists to normalize them into a single in-memory model for maintenance flows.

This is intentionally a larger architectural move than the minimum possible change. The project is personal and long-lived, so future expansion matters more than short-term implementation speed.

## Design

### 1. Unified read model

Add a new domain model centered on `ProjectSnapshot`.

Recommended module split:

- `src/pizhi/domain/project_state.py`
  - `ProjectSnapshot`
  - `ChapterState`
  - `ChapterArtifacts`
  - `ForeshadowingEntry`
  - `PendingChapter`
- `src/pizhi/services/project_snapshot.py`
  - `load_project_snapshot(project_root: Path) -> ProjectSnapshot`
  - file loading, normalization, and derived field assembly

The snapshot should aggregate:

- loaded config
- normalized chapter index records keyed by chapter number
- per-chapter state assembled from `index.jsonl`, `meta.json`, and artifact existence checks
- parsed timeline entries
- parsed foreshadowing entries
- derived views used by commands and reviews

The snapshot should expose at least these derived fields:

- `latest_chapter`
- `next_chapter`
- `recent_chapters`
- `pending_chapters`
- `active_foreshadowing`
- `near_payoff_foreshadowing`
- `overdue_foreshadowing`

The snapshot must degrade gracefully for partially initialized projects. Missing `index.jsonl`, `foreshadowing.md`, or `timeline.md` should produce empty collections rather than hard failures.

### 2. Foreshadowing normalization

Extend `src/pizhi/domain/foreshadowing.py` so it can parse full tracker entries, not only IDs.

Each parsed foreshadowing entry should capture:

- `id`
- lifecycle section: `Active`, `Referenced`, `Resolved`, or `Abandoned`
- priority when present
- description
- related characters
- raw `planned_payoff`
- normalized payoff window

Normalized payoff windows must support the architecture formats:

- `ch018`
- `ch010-ch015`
- `ch030+`

Recommended normalization shape:

- `start_chapter: int | None`
- `end_chapter: int | None`
- `open_ended: bool`

This normalization is shared by:

- `status` for near-payoff and overdue summaries
- `review --full` for overdue structural findings
- future archive and synopsis-review work

### 3. `review --full`

`review --full` remains deterministic in milestone 4. It does not perform AI semantic checks.

The command should now produce two classes of findings:

- chapter-level findings
  - file completeness
  - chapter continuity
  - characters declared in metadata but absent from chapter text
  - non-flashback timeline monotonicity
  - foreshadowing resolution legality
- project-level findings
  - chapter index and chapter directory mismatches
  - chapters in advanced states without required artifacts or metadata
  - obvious chapter-number gaps in active progress
  - overdue foreshadowing still left active or referenced

The report structure should expand beyond a flat issue list. A reasonable target shape is:

- `reviewed_chapters`
- `chapter_issues`
- `global_issues`
- `stats`

Output behavior:

- single-chapter review keeps writing `chXXX/notes.md`
- `review --full` also writes a global summary to `.pizhi/cache/review_full.md`
- CLI output prints a compact summary rather than dumping every issue inline

This keeps chapter notes chapter-scoped while giving full-review mode a durable project-level artifact.

### 4. `status`

`pizhi status` becomes a lightweight operations view over `ProjectSnapshot`.

It should display four sections:

- base progress
  - project name
  - planned chapter count
  - chapters per volume
  - latest chapter
  - next chapter
  - compiled volume count
  - chapter counts by lifecycle state
- recent chapters
  - latest 3-5 chapters by chapter number
  - chapter number, title, status, updated date
- foreshadowing overview
  - active foreshadowing count
  - near-payoff items
  - overdue items
- pending chapter queues
  - outlined but not drafted
  - drafted but not reviewed
  - reviewed but not compiled

The CLI remains text-first in this milestone. The goal is to stabilize the underlying snapshot and derived views, not to expand API surface area.

Derived rules:

- pending chapter queues come from `index.jsonl` lifecycle states, not content guessing
- recent chapters sort by chapter number descending, not filesystem timestamps
- near-payoff uses the latest known chapter against normalized payoff windows
- overdue means the payoff window upper bound is already behind the latest chapter while the foreshadowing is still active or referenced

### 5. Consumer refactor

These modules should be moved to the snapshot layer:

- `src/pizhi/services/status_report.py`
- `src/pizhi/services/consistency/structural.py`
- `src/pizhi/commands/status_cmd.py`
- `src/pizhi/commands/review_cmd.py`

The intent is not just code cleanup. It is to establish a stable maintenance-facing read boundary so later milestones can add archive awareness, synopsis candidate review, and AI review without duplicating file walking logic.

## Testing Strategy

Prefer snapshot-layer tests over command-only tests.

### Unit tests

- `tests/unit/test_project_snapshot.py`
  - initialized but mostly empty project
  - partially initialized project with missing globals
  - populated project with chapter metadata and artifacts
- `tests/unit/test_foreshadowing.py`
  - parse `ch018`
  - parse `ch010-ch015`
  - parse `ch030+`
- `tests/unit/test_status_report.py`
  - recent chapters
  - pending queues
  - near-payoff and overdue foreshadowing
- `tests/unit/test_structural_review.py`
  - project-level mismatches
  - overdue foreshadowing findings
  - existing chapter-level checks still work through the snapshot

### Integration tests

- `tests/integration/test_status_command.py`
  - verifies the new status sections appear in CLI output
- `tests/integration/test_review_command.py`
  - verifies `review --full` writes `.pizhi/cache/review_full.md`
  - verifies CLI summary output stays compact

### Regression rule

Milestones 1-3 remain green. New maintenance behavior should reuse the existing fixtures where practical rather than introducing a parallel sample project structure.

## Files

Expected new files:

- `src/pizhi/domain/project_state.py`
- `src/pizhi/services/project_snapshot.py`
- `tests/unit/test_project_snapshot.py`
- `tests/integration/test_status_command.py`
- `tests/integration/test_review_command.py`

Expected modified files:

- `src/pizhi/domain/foreshadowing.py`
- `src/pizhi/services/status_report.py`
- `src/pizhi/services/consistency/structural.py`
- `src/pizhi/commands/status_cmd.py`
- `src/pizhi/commands/review_cmd.py`
- `tests/unit/test_foreshadowing.py`
- `tests/unit/test_status_report.py`
- `tests/unit/test_structural_review.py`

## Acceptance Criteria

- A single loader can assemble project-wide state from the existing file layout without mutating any files
- `pizhi status` shows recent chapters, foreshadowing summaries, and pending queues
- `pizhi review --full` produces project-level findings and writes a cache report
- Existing review behavior for single chapters remains available
- The full test suite stays green after the refactor
