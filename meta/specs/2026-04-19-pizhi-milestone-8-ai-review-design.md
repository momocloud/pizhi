# Pizhi Milestone 8 Design: AI Review Layer

Date: 2026-04-19
Status: Proposed
Scope: Milestone 8

## 1. Goal

Milestone 8 introduces the architecture-defined B-class AI review layer on top of the existing deterministic review flow.

This milestone focuses on `review`-driven semantic review only. It does not introduce automatic post-write review, auto-fix, or multi-agent review debates.

The target outcome is:

- `pizhi review --chapter N --execute` runs A-class structural review first, then B-class AI review, and writes a partitioned `notes.md`
- `pizhi review --full --execute` runs A-class full-project review plus maintenance first, then B-class AI review, and writes a partitioned `review_full.md`
- AI review uses provider-backed execution with review-specific configuration overrides
- AI review keeps provider run artifacts for auditability, but does not require a separate `apply` phase

## 2. Non-Goals

This milestone explicitly does not include:

- automatic AI review after `write` or `continue`
- any automatic fix or patch application based on AI review output
- multi-provider fan-out review
- multi-agent or debate-style review
- more advanced summarization or semantic compression strategies
- changing the prompt-only writing flow

## 3. High-Level Architecture

Milestone 8 extends the current `review` pipeline instead of replacing it.

The architecture is divided into four layers:

1. A-class structural review
   - existing deterministic review remains the first stage
   - chapter-level and full-project structural issues stay authoritative for machine-checkable constraints

2. AI review context assembly
   - builds the review packet for either a single chapter or a full-project review
   - includes the A-class findings as explicit input to the model

3. AI review execution
   - uses provider-backed execution with review-specific configuration override support
   - persists prompt and response artifacts to the run store
   - parses and validates structured AI review output

4. Review document writing
   - writes partitioned `notes.md` for chapter review
   - writes partitioned `.pizhi/cache/review_full.md` for full review
   - preserves human-authored content while replacing only machine-managed sections

Proposed module split:

- `src/pizhi/domain/ai_review.py`
  - semantic review issue dataclasses and validation enums
- `src/pizhi/services/ai_review_context.py`
  - chapter and full-project AI review context assembly
- `src/pizhi/services/ai_review_service.py`
  - prompt construction, provider execution, output parsing, failure handling
- `src/pizhi/services/review_documents.py`
  - partitioned `notes.md` and `review_full.md` reading/writing
- `src/pizhi/commands/review_cmd.py`
  - orchestration only

## 4. Command Semantics

### 4.1 `pizhi review --chapter N`

- runs A-class structural review for the target chapter
- updates the `A 类结构检查` section in `chNNN/notes.md`
- does not call the provider

### 4.2 `pizhi review --chapter N --execute`

- runs A-class structural review first
- writes or updates the `A 类结构检查` section
- assembles chapter AI review context
- calls the provider using review-specific configuration
- validates the structured AI review output
- writes or updates the `B 类 AI 审查` section
- returns non-zero on AI review failure
- still keeps A-class results written to disk even if AI review fails

### 4.3 `pizhi review --full`

- runs A-class full-project structural review
- runs existing full maintenance
- writes `.pizhi/cache/review_full.md`
- does not call the provider

### 4.4 `pizhi review --full --execute`

- runs A-class full-project structural review
- runs existing full maintenance
- writes the base full review document
- assembles compressed full-project AI review context
- calls the provider using review-specific configuration
- validates the structured AI review output
- updates the `B 类 AI 审查` section in `.pizhi/cache/review_full.md`
- returns non-zero on AI review failure
- still keeps A-class and maintenance sections written to disk even if AI review fails

## 5. Review Document Contract

Milestone 8 changes chapter `notes.md` from a single overwritten report into a partitioned document.

### 5.1 Chapter `notes.md`

Target structure:

```markdown
## 作者备注

...

## A 类结构检查

...

## B 类 AI 审查

...
```

Rules:

- `作者备注` is preserved verbatim by the system
- if `作者备注` does not yet exist, the writer creates an empty placeholder section
- `A 类结构检查` is fully system-managed
- `B 类 AI 审查` is fully system-managed
- chapter review never rewrites the whole file blindly

### 5.2 Full Review Document

`.pizhi/cache/review_full.md` becomes a partitioned report with fixed sections:

```markdown
# Review Full

## Summary

...

## A 类结构检查

...

## Maintenance

...

## B 类 AI 审查

...
```

This gives the full review document a stable contract instead of ad hoc text concatenation.

## 6. AI Review Categories and Output Schema

The AI review layer uses fixed architecture-defined categories only.

Allowed categories:

- `人物一致性`
- `时间线合理性`
- `世界设定一致性`
- `因果一致性`
- `资源一致性`
- `Synopsis 覆盖性`

The model is not allowed to invent new categories.

Allowed severities:

- `高`
- `中`
- `低`

Each AI issue must use the same structured problem block shape already used by deterministic review:

```markdown
### 问题 1
- **类别**：人物一致性
- **严重度**：高
- **描述**：...
- **证据**：...
- **建议修法**：...
```

Output validation rules:

- every issue must include all five fields
- category must be in the fixed enum
- severity must be in the fixed enum
- malformed or partial issue blocks are rejected
- parse failures are treated as AI review failures, not as partially acceptable output

If no AI semantic issues are found, the `B 类 AI 审查` section writes a fixed no-issues message.

## 7. A/B Review Composition

Milestone 8 explicitly follows the architecture’s two-layer review model.

Execution order:

1. A-class deterministic review runs first
2. its findings are written to the document
3. the same findings are fed into the AI review context
4. B-class AI review produces additional semantic findings

This means AI review is supplemental, not parallel and not a replacement.

Benefits:

- deterministic checks remain authoritative for script-checkable constraints
- the model does not need to rediscover issues already found mechanically
- final chapter and full reports naturally present A/B findings together

## 8. Chapter AI Review Context

Single-chapter AI review uses a bounded context window rather than whole-book scan.

The context packet should include:

- target chapter:
  - `text.md`
  - `characters.md`
  - `relationships.md`
  - key `meta.json` fields
- previous chapter:
  - `text.md`
  - `characters.md`
  - `relationships.md`
- related global state:
  - `global/worldview.md`
  - relevant active/referenced foreshadowing entries
  - relevant `characters_index.md` entries
- A-class findings for the target chapter

This is sufficient for the target B-class checks without pulling the entire manuscript into a single request.

## 9. Full AI Review Context

`review --full --execute` must not send the full book raw to the model.

Instead it uses a compressed full-project packet derived from `ProjectSnapshot` and existing review outputs.

The packet should include at least:

- A-class full-project issues
- chapter issue summary
- active and overdue foreshadowing summary
- major-turning-point timeline summary
- recent chapter status summary
- chapter summaries or other compact per-chapter signals as needed
- maintenance findings summary

This milestone does not introduce multi-call review fan-out. Full-project AI review remains one compressed provider call per command invocation.

## 10. Provider Configuration

Milestone 8 introduces review-specific provider override support.

Configuration behavior:

- the existing provider block remains the default
- review-specific override fields are added for AI review execution
- if review-specific fields are absent, review falls back to the default provider config

The intended override surface is:

- `review_model`
- `review_base_url`
- `review_api_key_env`

If none are configured, AI review uses:

- `model`
- `base_url`
- `api_key_env`

`pizhi provider configure` should be extended so users can optionally configure review-specific values while preserving the current interactive-first UX.

## 11. Provider Execution and Run Artifacts

AI review writes final review documents directly after successful parsing. It does not use an `apply` step.

However, review execution still persists provider run artifacts for traceability.

Each `review --execute` provider call should keep normal run artifacts:

- manifest
- prompt
- raw payload
- normalized content
- error text when applicable

These artifacts live in the existing run store and reuse the current provider execution infrastructure where practical.

This gives:

- reproducibility
- debugging support
- evidence for why a given review result was produced

## 12. Failure Semantics

AI review failures must not discard deterministic review output.

### 12.1 Chapter Review Failure

If `review --chapter N --execute` fails at provider execution or AI output validation:

- command exits non-zero
- `A 类结构检查` remains updated
- `B 类 AI 审查` is updated with a failure explanation
- run artifacts are preserved if execution reached provider/run persistence

Typical failure reasons:

- provider request failed
- review API key missing
- provider returned empty/non-text output
- schema parse failed
- invalid category/severity enum

### 12.2 Full Review Failure

If `review --full --execute` fails at provider execution or AI output validation:

- command exits non-zero
- `Summary`, `A 类结构检查`, and `Maintenance` remain updated
- `B 类 AI 审查` is updated with a failure explanation
- run artifacts are preserved if execution reached provider/run persistence

## 13. Testing Strategy

### 13.1 Unit Tests

- AI review issue parsing
- category and severity validation
- chapter and full review context assembly
- partitioned `notes.md` writer behavior
- partitioned `review_full.md` writer behavior
- preservation of human-authored `作者备注`
- review config fallback logic

### 13.2 Integration Tests

- `pizhi review --chapter N --execute`
- `pizhi review --full --execute`
- provider failure behavior
- normalize/parse failure behavior
- schema-invalid AI output behavior
- fallback to default provider config when no review override is configured

### 13.3 Regression Requirements

- non-`--execute` review behavior must remain valid
- existing maintenance behavior for `review --full` must remain valid
- existing provider-first writing flow must not regress because of review-specific config changes

## 14. Implementation Scope

Included in Milestone 8:

- `review --chapter N --execute`
- `review --full --execute`
- A/B combined review flow
- partitioned `notes.md`
- partitioned `review_full.md`
- review-specific provider configuration override
- AI review run artifact persistence

Excluded from Milestone 8:

- automatic AI review after chapter writing
- automatic fix generation or patching
- multi-provider review fan-out
- multi-agent debate
- more advanced summarization algorithms

## 15. Acceptance Criteria

Milestone 8 is complete when all of the following are true:

- chapter review supports `--execute` and writes a partitioned `notes.md`
- full review supports `--execute` and writes a partitioned `review_full.md`
- AI output is validated against fixed category/severity/schema rules
- A-class findings are explicitly fed into B-class AI review
- chapter and full review preserve deterministic outputs on AI review failure
- review-specific provider overrides work and correctly fall back to default provider configuration
- run artifacts are preserved for review executions
- existing non-`--execute` review and maintenance behavior still pass
