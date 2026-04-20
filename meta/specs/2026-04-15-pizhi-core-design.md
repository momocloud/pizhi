# Pizhi Core Implementation Design

## Goal

Implement the architecture in `ARCHITECTURE.md` as a standalone Python CLI project rooted at `Pizhi/`, with deterministic file-system behavior first and AI orchestration layered on top after the core storage and validation flows are stable.

## Scope

- `Pizhi/` becomes the repository root for the implementation.
- The final architecture document remains the product source of truth during bootstrap, then moves under `docs/architecture/` in milestone 1 so docs live together.
- Delivery is staged so the first usable slice is a real tool, not a pile of stubs.

## Primary Decisions

### 1. Tech stack

- Language: Python 3.11+
- CLI: `argparse` with nested subcommands to match `pizhi init`, `pizhi outline expand`, `pizhi review --full`, and similar command shapes
- Serialization: `json`, `pathlib`, `dataclasses`, `datetime`, `re` from the standard library plus `PyYAML` for `config.yaml` and chapter frontmatter
- Tests: `pytest`

This keeps the runtime small while still handling the YAML-heavy parts of the architecture cleanly.

### 2. Delivery order

The implementation should not start with direct model integration. The project needs a stable content engine first:

1. Project bootstrap and status reporting
2. Chapter parsing, file writes, compile, and structural validation
3. AI-facing orchestration commands built on top of the stable engine

This matches the architecture's emphasis on "files as memory" and avoids mixing fragile LLM behavior with unproven storage logic.

### 3. Repository layout

```text
Pizhi/
├── ARCHITECTURE.md                        # Temporary location during bootstrap
├── docs/
│   ├── architecture/
│   │   └── ARCHITECTURE.md                # Final home for the architecture doc
│   └── superpowers/
│       └── specs/
├── src/
│   └── pizhi/
│       ├── cli.py
│       ├── commands/
│       │   ├── init_cmd.py
│       │   ├── status_cmd.py
│       │   ├── compile_cmd.py
│       │   ├── review_cmd.py
│       │   ├── brainstorm_cmd.py
│       │   ├── outline_expand_cmd.py
│       │   ├── write_cmd.py
│       │   └── continue_cmd.py
│       ├── core/
│       │   ├── paths.py
│       │   ├── config.py
│       │   ├── jsonl_store.py
│       │   ├── markdown_sections.py
│       │   ├── frontmatter.py
│       │   └── templates.py
│       ├── domain/
│       │   ├── chapter_index.py
│       │   ├── worldview.py
│       │   ├── foreshadowing.py
│       │   ├── timeline.py
│       │   └── characters_index.py
│       ├── services/
│       │   ├── project_init.py
│       │   ├── status_report.py
│       │   ├── chapter_context.py
│       │   ├── chapter_parser.py
│       │   ├── chapter_writer.py
│       │   ├── compiler.py
│       │   └── consistency/
│       │       ├── structural.py
│       │       └── ai_review.py
│       └── adapters/
│           ├── base.py
│           └── prompt_only.py
└── tests/
    ├── unit/
    └── integration/
```

The layout keeps command entrypoints thin and pushes file semantics into small focused modules.

## Milestones

### Milestone 1: Bootstrap a real project

Deliver a working repository with:

- Python package skeleton and test harness
- `pizhi init`
- `pizhi status`
- project path helpers and config loader/saver
- chapter index JSONL read/write
- project templates for `.pizhi/`, `manuscript/`, and starter files
- architecture doc moved into `docs/architecture/`

Success criteria:

- A user can run `pizhi init` in an empty novel workspace and get the documented directory tree
- A user can run `pizhi status` and see progress derived from `.pizhi/chapters/index.jsonl`
- Core bootstrap behavior is covered by integration tests

### Milestone 2: Finish the deterministic content engine

Deliver:

- chapter output parser for the YAML frontmatter plus Markdown sections schema in the architecture
- persistence of `text.md`, `characters.md`, `relationships.md`, `worldview_patch.md`, and `notes.md`
- worldview patch apply logic with exact bold-title matching
- foreshadowing and timeline update logic
- `pizhi compile`
- structural checks for chapter continuity, file completeness, time monotonicity, and foreshadowing reference legality
- `pizhi review` with at least the script-check layer fully working

Success criteria:

- A captured AI chapter response fixture can be parsed into the expected files
- Structural review finds invalid chapter outputs deterministically
- `pizhi compile` produces volume manuscripts from drafted chapters

### Milestone 3: Add orchestration commands

Deliver:

- `pizhi brainstorm`
- `pizhi outline expand`
- `pizhi write`
- `pizhi continue`
- prompt builders and hook templates for pre/post chapter flows
- adapter boundary for future model integration
- checkpoint summaries every 3 chapters for `continue`

Success criteria:

- Commands can build prompts/context windows and persist outputs through the milestone 2 engine
- AI integration is isolated behind `adapters/` so provider changes do not affect file semantics

## Implementation Path

### Phase A: Project skeleton first

- Initialize Git and baseline ignores
- Add `pyproject.toml`, package entrypoint, `src/` layout, and pytest config
- Move `ARCHITECTURE.md` under `docs/architecture/` and leave a short root pointer if needed

### Phase B: Build the storage primitives

- Implement config and JSONL index I/O
- Implement template rendering for `pizhi init`
- Implement status reporting against real project state

### Phase C: Build the chapter engine

- Parse frontmatter and sectioned Markdown
- Write chapter artifacts
- Apply worldview patches and update global trackers
- Add structural validation and compilation

### Phase D: Build orchestration on top

- Context assembly from synopsis, worldview, rules, recent chapters, foreshadowing, and characters index
- Prompt-only adapter first, provider adapters later
- Workflow commands for brainstorm, outline, write, continue, and AI-assisted review

## Error Handling

- Invalid YAML frontmatter is a hard error
- Missing required Markdown sections are hard errors
- Worldview patch `Modified` and `Retracted` operations fail when the bold title does not match exactly one current entry
- `synopsis_candidate.md` is preserved when coverage checks fail
- `status` must degrade gracefully when a project is partially initialized

## Testing Strategy

- Unit tests for YAML/frontmatter parsing, section splitting, worldview patching, foreshadowing updates, and timeline checks
- Integration tests for `init`, `status`, `compile`, and `review`
- Golden-file fixtures for representative chapter outputs and expected file trees
- One end-to-end fixture per milestone to keep regression coverage honest

## Git Strategy

- Use `main` as the default branch for the new repository
- Keep milestone work in small reviewable commits
- Do not mix refactors with command behavior changes in the same commit
- Treat the architecture and design docs as tracked project artifacts, not throwaway notes

## Non-Goals For The First Slice

- Direct integration with any single hosted model provider
- Multi-agent execution
- Fancy TUI output
- Archive rotation automation before the chapter engine exists

## Assumptions

- The initial implementation can require Python plus `PyYAML`
- AI-facing commands may start in prompt-oriented mode before provider-specific automation is added
- `ARCHITECTURE.md` remains authoritative when a code path and the doc disagree until the doc is intentionally updated
