# Pizhi Design: UV Git Distribution

Date: 2026-04-21
Status: Proposed
Scope: Git-backed `uv` distribution for the `pizhi` CLI

## 1. Goal

This change makes `pizhi` consumable as a normal CLI through `uv` directly from the public GitHub repository.

The target outcome is:

- users can run `pizhi` without a local editable checkout by using `uvx --from git+https://github.com/momocloud/pizhi.git ...`
- users can install `pizhi` as a persistent tool by using `uv tool install git+https://github.com/momocloud/pizhi.git`
- the same workflow is documented and supported for a fixed Git tag, starting with `v0.1.0`
- package metadata and documentation are aligned with Git-based distribution rather than only local source checkout usage
- the repository includes enough contract coverage that the documented `uv` consumption paths do not silently drift

## 2. Non-Goals

This change explicitly does not include:

- PyPI publishing
- GitHub Release automation
- release scripts or CI-based publishing
- a new skill or agent integration surface
- changes to `pizhi` CLI behavior
- provider behavior changes

## 3. Primary Decisions

### 3.1 Git-backed `uv` distribution is the supported distribution target

This milestone targets public Git consumption through `uv`, not package-index publishing.

The primary supported forms are:

```bash
uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help
uv tool install git+https://github.com/momocloud/pizhi.git
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0
```

### 3.2 Tagged consumption is a first-class supported path

This change does not treat `@v0.1.0` as an optional example only.

It is part of the intended distribution surface because:

- automation and agent callers benefit from stable refs
- untagged `main` consumption is useful for trying the latest branch state
- tagged consumption is the safer default for reproducible CLI usage

### 3.3 Public documentation prefers HTTPS Git URLs

The repository documentation should present HTTPS Git URLs as the canonical examples.

SSH and other Git URL variants may work, but they should not become the primary documented path for first-time users.

### 3.4 Package metadata and GitHub-facing docs should remain separate

The GitHub landing page and the package long description have different constraints.

`README.md` remains the repository landing page and may contain repository-relative links.

`README-package.md` remains the package-facing description referenced by `pyproject.toml` so package metadata is not forced to rely on repository-relative links that break outside GitHub.

### 3.5 This milestone includes creation and publication of the first release tag

The repository currently has package version `0.1.0` and changelog section `v0.1.0`, but no Git tag.

This milestone should create and push:

- `v0.1.0`

The tag should point to the already-prepared public baseline on `main`.

## 4. Supported User Flows

### 4.1 Run without installation

Users should be able to run:

```bash
uvx --from git+https://github.com/momocloud/pizhi.git pizhi status
```

and:

```bash
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help
```

without additional packaging steps.

### 4.2 Install as a persistent local tool

Users should be able to run:

```bash
uv tool install git+https://github.com/momocloud/pizhi.git
```

and:

```bash
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0
```

and then call:

```bash
pizhi --help
```

through the installed tool entry point.

### 4.3 Recommended usage guidance

Documentation should state:

- use `main` when you intentionally want the latest repository state
- use `@v0.1.0` when you want a stable, reproducible tool version

This guidance is especially important for external agent tools and automation scripts.

## 5. Documentation Changes

### 5.1 Repository landing page

`README.md` should gain a short section for `uv` consumption.

It should cover:

- running with `uvx --from ...`
- installing with `uv tool install ...`
- the difference between `main` and `@v0.1.0`

It should remain concise and should not turn into release-process documentation.

### 5.2 Package readme

`README-package.md` should mention that the CLI can be consumed from the public Git repository with `uvx` and `uv tool install`.

It should remain safe for package metadata rendering and avoid repository-relative doc-link assumptions.

### 5.3 Getting-started guide

`docs/guides/getting-started.md` should gain a short acquisition section before the main workflow.

It should clearly separate:

- local source-checkout usage
- Git-backed `uv` consumption

### 5.4 Contributor guidance

`CONTRIBUTING.md` should document the relationship between the package version and the public tag baseline.

It does not need a full release runbook, but contributors should be able to tell that:

- `0.1.0` maps to `v0.1.0`
- future public Git distribution should keep package version, changelog, and tag naming aligned

## 6. Package and Repository Metadata

This milestone should preserve the current console-script entry:

- `pizhi = "pizhi.cli:main"`

and ensure the package metadata remains compatible with Git-based installation through `uv`.

Expected metadata shape:

- package name remains `pizhi`
- version remains `0.1.0`
- `pyproject.toml` `readme` continues to point to `README-package.md`

No new build backend or packaging tool should be introduced.

## 7. Tagging Decision

This milestone should create `v0.1.0` locally and push it to `origin`.

The tag is part of the deliverable because the documented `@v0.1.0` install commands should be real, not hypothetical.

This is a manual tag publication step, not an automated release pipeline.

## 8. Expected Files

Expected touched or created paths include:

- `README.md`
- `README-package.md`
- `docs/guides/getting-started.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md` if small wording alignment is needed
- `pyproject.toml` only if Git distribution wording or metadata alignment requires it
- `tests/integration/test_docs_contract.py`
- `tests/integration/test_repository_layout_contract.py`

Expected Git operations include:

- creating `v0.1.0`
- pushing `main`
- pushing `v0.1.0`

## 9. Verification

Verification should cover three layers.

### 9.1 Repository and docs contracts

Confirm that docs and metadata reference the supported `uv` Git consumption paths.

At minimum, repository contract tests should protect:

- the documented GitHub repository URL
- `README-package.md` remaining the package long description target
- the presence of `uvx --from ...` and `uv tool install ...` guidance in the intended docs

### 9.2 Local CLI regression

Run:

```bash
python -m pizhi --help
python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py tests/integration/test_cli_help_contract.py -q --tb=short -rfE
python -m pytest tests/unit tests/integration -q --tb=short -rfE
```

### 9.3 Git-backed `uv` smoke checks

Run at least:

```bash
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0 --force
pizhi --help
```

If practical, also verify the untagged `main` path:

```bash
uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help
```

## 10. Completion Criteria

This Git-distribution change is complete when:

- the repository documents `uvx` and `uv tool install` Git URLs clearly
- `@v0.1.0` is a real pushed tag
- package metadata remains compatible with Git-based `uv` installation
- local regression tests still pass
- at least one tagged Git-backed `uv` run path and one tagged install path have been exercised successfully
