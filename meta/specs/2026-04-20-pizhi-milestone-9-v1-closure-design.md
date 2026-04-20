# Pizhi Milestone 9 Design: V1 Closure

Date: 2026-04-20
Status: Proposed
Scope: Milestone 9

## 1. Goal

Milestone 9 closes the remaining v1 architecture gaps without expanding the product into a new capability tier.

The target outcome is:

- provider execution supports project-level fixed model routing for the major command families
- `compile` supports volume, single-chapter, and continuous chapter-range targets
- the current snapshot contract is formally frozen for v1 as `Markdown + frontmatter + index.jsonl`
- the existing provider-first and AI-review flows are hardened with additional routing and determinism regression coverage

This milestone is the last "core-path closure" step before milestone 10 focuses on extensibility and release polish.

## 2. Non-Goals

This milestone explicitly does not include:

- multi-provider routing or fan-out
- per-run or per-session temporary model overrides
- new provider adapters
- a new snapshot format or storage migration
- new AI review categories or new post-write automation
- multi-agent execution

## 3. Primary Decisions

### 3.1 Model routing is project-level and fixed

Milestone 9 adds project-level model routing fields in configuration.

Routing is decided by project config only. There is no CLI-level temporary override in this milestone.

### 3.2 `compile` grows by target mode, not by ad hoc flags

`compile` should expose three clear mutually exclusive target types:

- by volume
- by single chapter
- by continuous chapter range

This keeps the CLI understandable while covering the real v1 use cases.

### 3.3 Snapshot format is frozen for v1

The architecture open question around snapshot format is closed in milestone 9.

v1 continues to use:

- Markdown chapter/global documents
- YAML frontmatter for generated chapter responses
- `index.jsonl` as chapter-state truth

No YAML migration or alternate snapshot serialization is introduced in this milestone.

## 4. Model Routing Design

Milestone 9 extends the existing provider configuration from "default model plus optional review override" into a fixed project-level routing table.

The connection layer remains shared:

- `provider`
- `base_url`
- `api_key_env`

The default model layer remains:

- `model`
- `review_model`

The new route-level fields are:

- `brainstorm_model`
- `outline_model`
- `write_model`
- `continue_model`
- `review_model`

Rules:

- `brainstorm --execute` uses `brainstorm_model`, falling back to `model`
- `outline expand --execute` uses `outline_model`, falling back to `model`
- `write --execute` uses `write_model`, falling back to `model`
- `continue --execute` uses `continue_model`, falling back to `model`
- `review --execute` keeps using `review_model`, falling back to `model`

Milestone 9 does not split `continue` into separate outline/write routing keys. Both checkpoint phases use the same `continue_model`.

## 5. Provider Configuration UX

`pizhi provider configure` remains the only project-facing configuration command for provider settings.

Milestone 9 extends it so users can configure the new route-level model fields while preserving the current UX:

- interactive-first flow remains the default
- flag-driven parameter mode remains supported
- base connection settings are still configured once
- omitted route fields continue to inherit from the default model layer

This keeps the configuration surface explicit without introducing a second provider-management command.

## 6. Provider Execution Integration

Milestone 9 should keep the existing provider execution infrastructure and add route resolution before request execution.

Recommended boundary:

- command services continue to build prompt requests as they do today
- route resolution happens in provider-facing orchestration code, not in every command module separately
- the final execution metadata written to the run store must include the actually selected model

This ensures run artifacts remain auditable when different commands use different routed models.

`continue --execute` should also record the resolved `continue_model` in its generated run metadata so checkpoint/session history reflects the actual model used.

## 7. `compile` Command Design

Milestone 9 expands `compile` into three mutually exclusive target modes:

- `pizhi compile --volume N`
- `pizhi compile --chapter N`
- `pizhi compile --chapters A-B`

The command must reject:

- missing target mode
- multiple target modes provided together
- invalid chapter range syntax
- descending or empty ranges

### 7.1 Output paths

Compiled manuscript outputs should be:

- volume: `manuscript/vol_XX.md`
- single chapter: `manuscript/chXXX.md`
- range: `manuscript/chXXX-chYYY.md`

### 7.2 Content rules

Compiled manuscript content continues to be reader-facing text only:

- stable title/header
- chapters concatenated in ascending order
- no internal metadata blocks in the manuscript output

### 7.3 Status updates

Only chapters actually included in the compile target are updated to `compiled`.

The command must not silently skip invalid chapters inside the target. If a target chapter lacks required text or is otherwise not compilable, the command fails instead of performing partial success.

## 8. Stability Hardening

Milestone 9 adds closure-oriented hardening, not broad refactoring.

The hardening focus is:

- model-routing fallback behavior
- `continue` routed-model consistency across outline and write checkpoints
- `compile` target validation and failure behavior
- additional malformed review-document coverage
- stronger prompt-determinism regression checks
- stronger bounded-context regression checks for provider-backed flows

This milestone is where the provider-first and AI-review paths become "v1 stable" rather than merely feature-complete.

## 9. Documentation Closure

Milestone 9 should also close the remaining architecture documentation gap.

Required documentation updates:

- mark the snapshot-format open question as decided in `ARCHITECTURE.md`
- document the model-routing behavior in the architecture or related user-facing docs
- document the new `compile` target modes

This milestone should leave no major ambiguity around the v1 storage contract or the expected model-selection behavior.

## 10. Expected Files

Expected modified files:

- `src/pizhi/core/config.py`
- `src/pizhi/commands/provider_cmd.py`
- `src/pizhi/services/provider_execution.py`
- `src/pizhi/services/continue_execution.py`
- `src/pizhi/services/ai_review_service.py` when review route selection needs shared resolution
- `src/pizhi/commands/compile_cmd.py`
- `src/pizhi/services/compiler.py`
- `src/pizhi/cli.py`
- `docs/architecture/ARCHITECTURE.md`

Expected new or expanded tests:

- `tests/unit/test_config.py`
- `tests/unit/test_provider_execution.py`
- `tests/unit/test_continue_execution.py`
- `tests/unit/test_compiler.py`
- `tests/integration/test_provider_configure_command.py`
- `tests/integration/test_compile_command.py`
- targeted review/prompt determinism regression tests where current coverage is weak

## 11. Testing Strategy

### 11.1 Unit tests

- provider config round-trip for route-level model fields
- route fallback behavior when specific route fields are omitted
- `continue` execution using the routed model in both checkpoint phases
- single-chapter compile
- range compile
- compile target validation failures

### 11.2 Integration tests

- `provider configure` interactive and parameter-driven model-route persistence
- `brainstorm / outline / write / continue / review` selecting the expected model
- `compile --volume`
- `compile --chapter`
- `compile --chapters A-B`
- failure behavior when compile targets are incomplete or invalid

### 11.3 Regression rule

Milestones 1-8 must remain green.

The milestone 9 verification path should continue using the quieter full-suite command by default:

`python -m pytest tests/unit tests/integration -q --tb=short -rfE`

## 12. Acceptance Criteria

Milestone 9 is complete when all of the following are true:

- project config supports fixed model routing for the main command families
- routed provider execution records the actually selected model in run metadata
- `continue --execute` uses one explicit routed model consistently across both checkpoint phases
- `compile` supports volume, single-chapter, and continuous chapter-range targets
- compile target modes are mutually exclusive and validate input clearly
- only compiled target chapters have their status updated
- the v1 snapshot-format decision is documented and the open question is closed
- existing provider-first writing, checkpoint orchestration, and AI review flows remain green
