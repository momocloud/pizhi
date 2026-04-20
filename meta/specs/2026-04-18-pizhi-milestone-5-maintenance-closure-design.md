# Pizhi Milestone 5 Maintenance Closure Design

## Goal

Close the first maintenance loop in Pizhi by adding deterministic synopsis-candidate review, fixed-range archive rotation, and the remaining milestone 4 maintenance regressions.

After this milestone:

- `synopsis_candidate.md` can be deterministically reviewed and promoted into `synopsis.md`
- timeline and foreshadowing archives rotate in fixed 50-chapter blocks
- maintenance work can run from `write`, `continue`, and `review --full`
- `status` and `review` stop disagreeing on tracked foreshadowing and chapter continuity

## Scope

- Fix the remaining milestone 4 maintenance regressions
- Add deterministic `synopsis_candidate.md` review and promotion
- Add fixed 50-chapter archive rotation for timeline and foreshadowing
- Add shared maintenance orchestration for post-write and full-review flows
- Extend the snapshot layer just enough to support archive-aware maintenance decisions

## Non-Goals

- AI semantic synopsis review
- Provider-backed model integration
- Sliding-window archive rotation
- New persistent state files such as `archive_index.json`
- Refactoring the write pipeline into a transactional system

## Primary Decisions

### 1. Maintenance stays deterministic

This milestone does not add AI judgment. All new behavior must be explainable from filesystem state and explicit markers.

### 2. New maintenance behavior lives in dedicated services

Archive rotation and synopsis review are not folded into `chapter_writer.py` as core write-path logic. They live behind dedicated maintenance services and are invoked from orchestration entry points.

### 3. Archive rotation uses fixed 50-chapter blocks

Archive files are range-based and closed:

- `ch001-ch050`
- `ch051-ch100`
- `ch101-ch150`

There is no sliding live window and no single-chapter archive churn.

Archive file names are exact and zero-padded:

- timeline archive: `.pizhi/archive/timeline_ch001-050.md`
- foreshadowing archive: `.pizhi/archive/foreshadowing_ch001-050.md`

For every sealed range, archive rotation writes at most one timeline file and one foreshadowing file. Range discovery is filename-driven from these exact patterns.

### 4. Synopsis review uses explicit coverage markers

Deterministic synopsis review does not infer meaning from prose. Instead, the candidate file carries a machine-readable coverage declaration for the required storyline elements.

## Design

### 1. Regression fixes carried into milestone 5

Two confirmed maintenance regressions are treated as required work at the start of the milestone:

- `status` must include both `Active` and `Referenced` foreshadowing entries when computing near-payoff and overdue summaries
- single-chapter structural review must restore chapter continuity checking instead of only surfacing chapter gaps in `review --full`

These fixes are part of the milestone acceptance criteria because milestone 5 builds on the maintenance layer introduced in milestone 4.

### 2. Dedicated maintenance services

Add three focused services:

- `src/pizhi/services/synopsis_review.py`
  - reads and validates `global/synopsis_candidate.md`
  - derives required deterministic coverage from `ProjectSnapshot`
  - returns a structured result describing pass/fail, missing coverage items, and whether promotion happened
- `src/pizhi/services/archive_service.py`
  - computes sealed 50-chapter archive ranges from current project progress
  - archives eligible timeline and foreshadowing entries
  - guarantees idempotent behavior when archive files already exist
- `src/pizhi/services/maintenance.py`
  - orchestrates post-write and full-maintenance flows
  - composes synopsis review and archive rotation without owning parsing logic

The file system remains the only source of truth. These services read and rewrite existing truth files but do not introduce a new shadow state format.

### 3. Snapshot extensions

Extend `ProjectSnapshot` and the loader to expose the data maintenance services need:

- live `timeline_entries`
- `active_or_referenced_foreshadowing`
- `major_turning_points`
- `eligible_archive_ranges`
- `existing_archive_ranges`

Archive awareness should stay lightweight:

- live commands still read primarily from live files
- archive files are discovered by file name and loaded only when needed
- no full archive materialization is required for normal `status`

`ProjectSnapshot` should continue to degrade gracefully if archive files do not exist yet.

### 4. Deterministic synopsis candidate review

`global/synopsis_candidate.md` becomes a two-part document:

- human-readable synopsis body
- machine-readable `## coverage_markers` section

Recommended marker shape:

```markdown
## coverage_markers

- foreshadowing_ids: F001, F003, F010
- major_turning_points: T003-02, T010-01, T010-02
```

The deterministic review contract is:

1. candidate synopsis body must be non-empty
2. `coverage_markers` must exist and parse cleanly
3. marker IDs must exactly cover the required deterministic coverage set

Required coverage is derived from:

- all live `Active` foreshadowing entries
- all live `Referenced` foreshadowing entries
- all major turning points across live timeline and archived timeline files

If review passes:

- promote the synopsis body into `global/synopsis.md`
- remove `global/synopsis_candidate.md`
- write a success summary into `.pizhi/cache/synopsis_review.md`

If review fails:

- keep `global/synopsis_candidate.md`
- keep the current `global/synopsis.md`
- write `.pizhi/cache/synopsis_review.md` with missing markers, malformed markers, or empty-body findings

The promoted `synopsis.md` must not include the marker block. The marker block is a review artifact only.

### 5. Fixed-range archive rotation

Archive rotation is computed from `latest_chapter`.

Examples:

- latest chapter `ch049`: no sealed archive range
- latest chapter `ch050`: sealed range `ch001-ch050`
- latest chapter `ch118`: sealed ranges `ch001-ch050` and `ch051-ch100`

`archive_service` then subtracts already existing archive ranges and processes only the missing ones.

#### Timeline archive rules

- archive by event chapter number
- entries for chapters inside the sealed range move into `.pizhi/archive/timeline_ch001-050.md`-style files
- archived entries are removed from live `global/timeline.md`

#### Foreshadowing archive rules

- only `Resolved` and `Abandoned` entries are eligible
- `Active` and `Referenced` always stay live
- archive placement is determined by the closing chapter, not by introduction chapter
- archived entries for a sealed range are written into a single `.pizhi/archive/foreshadowing_ch001-050.md`-style file for that range

To support this, tracker entries must carry explicit closing metadata:

- resolved entries: `Resolved In: chNNN`
- abandoned entries: `Abandoned In: chNNN`

If a closed foreshadowing entry lacks its closing chapter:

- do not archive it
- keep it live
- report it as an archive metadata gap in the maintenance result

This is intentionally conservative. Archive rotation must never guess.

#### Archive discovery and idempotency

Archive discovery uses the exact filename patterns below:

- `timeline_ch{start:03d}-{end:03d}.md`
- `foreshadowing_ch{start:03d}-{end:03d}.md`

For a given sealed range:

- if neither archive file exists, the service may create one or both as needed
- if one file exists and the other does not, the missing file may still be created independently
- if an existing archive file already matches the expected content, the operation is a no-op for that file
- if an existing archive file conflicts with the expected content, report a maintenance finding and do not overwrite it

This allows timeline and foreshadowing archives to remain independently idempotent while still sharing the same sealed range contract.

### 6. Entry-point orchestration

Add maintenance orchestration in three places:

- `write`
  - after chapter persistence succeeds, call `maintenance.run_after_write(...)`
  - run synopsis review, then archive rotation
  - maintenance failures do not roll back chapter persistence
- `continue`
  - reuse the same per-chapter post-write maintenance behavior
  - surface maintenance summaries at the existing checkpoint boundary
- `review --full`
  - call `maintenance.run_full_maintenance(...)`
  - use it to catch up missed synopsis review and archive work
  - include maintenance findings in the full-review summary

The maintenance layer is additive. Chapter generation remains successful even when post-write maintenance reports findings.

### 7. Failure semantics

#### Synopsis review failure

- chapter outputs remain persisted
- `synopsis_candidate.md` remains in place
- `synopsis.md` is not replaced
- `.pizhi/cache/synopsis_review.md` explains the failure

#### Archive failure or data gap

- live files are left unchanged for the affected entries
- archive files are not partially trusted if content conflicts with expected ranges
- maintenance results report the inconsistency instead of forcing a move

#### Consistency between maintenance views

`status`, chapter review, and full review must align on the underlying rules for:

- tracked foreshadowing states
- overdue windows
- chapter continuity

Milestone 5 should reduce cross-command disagreement, not add more.

## Data Contracts

### 1. Foreshadowing tracker additions

Update tracker parsing and formatting so closed entries can carry explicit closing-chapter metadata.

Examples:

```markdown
## Resolved

### F000
- **Description**: 阿坤的失踪
- **Resolved In**: ch005
- **Resolution**: 阿坤被雷老板扣押，在码头货仓被找到

## Abandoned

### F099
- **Description**: 最初设想的神秘组织线
- **Abandoned In**: ch010
- **Abandon Reason**: 大纲调整，该组织线被合并到雷老板势力线中
```

When `chapter_writer` resolves a foreshadowing entry, it should write `Resolved In: chNNN` automatically.

### 2. Synopsis candidate markers

`synopsis_candidate.md` should reserve a dedicated review section:

```markdown
## coverage_markers

- foreshadowing_ids: F001, F003
- major_turning_points: T002-01, T010-02
```

Parsing should be strict enough to reject malformed markers but tolerant enough to accept empty sets where appropriate.

## Files

Expected new files:

- `src/pizhi/services/synopsis_review.py`
- `src/pizhi/services/archive_service.py`
- `src/pizhi/services/maintenance.py`
- `tests/unit/test_synopsis_review.py`
- `tests/unit/test_archive_service.py`

Expected modified files:

- `src/pizhi/domain/project_state.py`
- `src/pizhi/domain/foreshadowing.py`
- `src/pizhi/domain/timeline.py`
- `src/pizhi/services/project_snapshot.py`
- `src/pizhi/services/chapter_writer.py`
- `src/pizhi/services/status_report.py`
- `src/pizhi/services/consistency/structural.py`
- `src/pizhi/services/continue_service.py`
- `src/pizhi/commands/review_cmd.py`
- `tests/unit/test_status_report.py`
- `tests/unit/test_structural_review.py`
- `tests/integration/test_review_command.py`
- `tests/integration/test_write_command.py`

## Testing Strategy

### Unit tests

- `status` includes `Referenced` entries in near-payoff and overdue summaries
- single-chapter review restores chapter continuity findings
- synopsis candidate parser accepts a valid marker block and rejects malformed markers
- synopsis review promotes a valid candidate and preserves an invalid candidate
- archive range calculation seals only complete 50-chapter blocks
- archive rotation is idempotent
- foreshadowing archive skips closed entries that lack `Resolved In` or `Abandoned In`

### Integration tests

- writing a chapter with `synopsis_changed: true` can promote a valid candidate into `synopsis.md`
- invalid candidate review preserves `synopsis_candidate.md` and writes `.pizhi/cache/synopsis_review.md`
- `review --full` can backfill missing archive work into `.pizhi/archive/`
- running the same maintenance flow twice does not duplicate archive output or corrupt live trackers

### Regression rule

Milestones 1-4 remain green. New maintenance behavior must not regress existing deterministic chapter parsing, persistence, status, compile, or review flows.

## Acceptance Criteria

- `status` and `review` agree on tracked foreshadowing windows and chapter continuity behavior
- `synopsis_candidate.md` can be deterministically reviewed and either promoted or preserved with an explicit cache report
- archive rotation produces fixed 50-chapter range files and removes only safely archivable live entries
- archive rotation is idempotent and does not require a new persistent index file
- `write`, `continue`, and `review --full` can all trigger the shared maintenance layer
- the full test suite remains green after the milestone
