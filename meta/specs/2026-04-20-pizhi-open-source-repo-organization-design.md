# Pizhi Design: Open Source Repository Organization

Date: 2026-04-20
Status: Proposed
Scope: Repository organization and documentation packaging

## 1. Goal

This change reorganizes the Pizhi repository into a more conventional GitHub open-source layout without changing product behavior.

The target outcome is:

- public-facing documentation is clearly separated from internal implementation-process documents
- the repository root exposes the files a new GitHub visitor expects to find
- the `README` becomes the single public entry point for onboarding and navigation
- package metadata reflects the public repository entry points
- the resulting repository is easier to read, contribute to, and maintain as a normal open-source project

## 2. Non-Goals

This change explicitly does not include:

- CLI behavior changes
- source layout changes under `src/`
- test layout changes under `tests/`
- architecture rewrites beyond link and location cleanup
- new product features
- removal of historical implementation-process documents

## 3. Primary Decisions

### 3.1 Public docs and internal process docs are separated

The `docs/` tree should contain only user-facing and contributor-facing documentation.

Internal process artifacts such as milestone specs and plans move out of `docs/` into a dedicated root-level `meta/` tree.

Recommended target structure:

- `docs/architecture/`
- `docs/guides/`
- `meta/specs/`
- `meta/plans/`

### 3.2 The repository keeps its stable code layout

The existing code and test roots remain unchanged:

- `src/`
- `tests/`

This change is about packaging and navigation, not refactoring the application layout.

### 3.3 Root-level repository metadata should match common GitHub expectations

The repository root should contain the standard project entry and governance files:

- `README.md`
- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `CHANGELOG.md`

### 3.4 The root `ARCHITECTURE.md` remains a compatibility pointer

The canonical architecture document remains at `docs/architecture/ARCHITECTURE.md`.

The root `ARCHITECTURE.md` should stay as a thin pointer document so existing links and historical references do not break.

## 4. Documentation Structure

### 4.1 Public documentation surface

The public docs surface should remain intentionally small.

Recommended public structure:

- `README.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/guides/getting-started.md`
- `docs/guides/recovery.md`

An optional lightweight docs index may be added only if it clearly improves navigation.

### 4.2 Internal process documentation

Existing implementation-process documents should move from:

- `docs/superpowers/specs/`
- `docs/superpowers/plans/`

to:

- `meta/specs/`
- `meta/plans/`

The content does not need rewriting during this move. The primary purpose is boundary clarification.

### 4.3 Link hygiene

Any public-facing links that currently point to `docs/superpowers/...` should be updated to avoid exposing internal process paths as part of the public docs surface.

Internal cross-links between specs and plans may continue to exist after relocation as long as they resolve correctly.

## 5. README Role

`README.md` should act as the GitHub landing page and do only the following:

- identify the project
- summarize core capabilities
- provide the shortest viable getting-started flow
- point to the main guides and architecture document
- point contributors to collaboration and security documents

The `README` should not become a long-form design document.

## 6. Repository Metadata and Governance Files

This change should add or normalize the following files.

### 6.1 License

The repository license is:

- `MIT`

### 6.2 Contribution guidance

`CONTRIBUTING.md` should cover:

- local setup
- recommended test command
- pull request expectations
- documentation placement conventions

### 6.3 Community and security files

Add:

- `CODE_OF_CONDUCT.md`
- `SECURITY.md`

These should use standard open-source wording with project-specific contact/process guidance where needed.

### 6.4 Changelog

Add `CHANGELOG.md` with a clean initial structure suitable for future releases.

It should not invent a detailed fake release history.

### 6.5 GitHub templates

Add:

- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/pull_request_template.md`

These should be concise and aligned with the project's workflow.

## 7. Package Metadata

`pyproject.toml` should reflect the public repository entry point.

The `readme` field should point to:

- `README.md`

and not to the architecture pointer or an internal document.

## 8. Expected Files

Expected touched or created paths include:

- `README.md`
- `ARCHITECTURE.md`
- `pyproject.toml`
- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/pull_request_template.md`
- `meta/specs/`
- `meta/plans/`
- moved files formerly under `docs/superpowers/`

## 9. Verification

Verification should cover three layers.

### 9.1 Structure and links

Confirm:

- the new `meta/` tree exists
- the public docs tree no longer carries internal milestone process docs
- the main documentation links resolve to the new locations
- GitHub templates exist at the expected paths

### 9.2 Packaging and CLI metadata

Confirm:

- `pyproject.toml` points to `README.md`
- `python -m pizhi --help` still works

### 9.3 Regression

Run the full test suite using the quieter project-default command for this session:

```bash
python -m pytest tests/unit tests/integration -q --tb=short -rfE
```

## 10. Completion Criteria

This repository-organization change is complete when:

- public and internal docs are clearly separated
- standard GitHub open-source metadata files are present
- the repository root looks conventional to a first-time visitor
- documentation links are coherent after the move
- package metadata is aligned with the public entry point
- tests still pass without behavioral regressions
