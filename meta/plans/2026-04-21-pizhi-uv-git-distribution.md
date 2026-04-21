# Pizhi UV Git Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `pizhi` a documented, contract-tested `uv` CLI that users and agents can run or install directly from the public GitHub repository URL, including a stable `v0.1.0` tag path.

**Architecture:** Keep the existing Python package and console script unchanged, and treat this milestone as a distribution/documentation closure. Extend the public docs and repository-contract tests so the repository consistently advertises four supported Git-backed `uv` entry points, then finish with verification and release-handoff notes for tagging `v0.1.0` on merged `main`.

**Tech Stack:** Python 3.14, setuptools console scripts, pytest integration contracts, Markdown docs, Git tags, `uvx`, `uv tool install`

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\uv-git-distribution`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -q --tb=short -rfE`
  - Observed while writing this plan: `317 passed in 94.41s`

## File Map

- `README.md`: public landing page; add a short `uv` Git install/run section that documents `main` and `@v0.1.0` entry points plus when to prefer each.
- `README-package.md`: package-index-safe readme; add Git-backed `uvx` and `uv tool install` examples without repo-relative documentation links.
- `docs/guides/getting-started.md`: add the canonical “how to acquire the CLI” section for local source, Git-backed `uvx`, and Git-backed `uv tool install`.
- `CONTRIBUTING.md`: document the `v0.1.0` Git tag expectation and keep contributor guidance aligned with the new distribution story.
- `CHANGELOG.md`: keep the public baseline clear and note the Git-backed `uv` distribution addition if needed.
- `pyproject.toml`: preserve `name`, `version`, `readme`, and console-script metadata; only touch if a contract exposes drift.
- `meta/specs/2026-04-21-pizhi-uv-git-distribution-design.md`: approved design doc; leave unchanged.
- `meta/plans/2026-04-21-pizhi-uv-git-distribution.md`: this plan; update verification notes if the observed results change during implementation.
- `tests/integration/test_docs_contract.py`: extend public-doc assertions to cover Git-backed `uv` install/run guidance in `README.md`, `README-package.md`, and the getting-started runbook.
- `tests/integration/test_repository_layout_contract.py`: extend repository/documentation contract coverage for package metadata and contributor docs that support tagged Git distribution.

### Task 1: Add UV Git Distribution Contract Tests

**Files:**
- Modify: `tests/integration/test_docs_contract.py`
- Modify: `tests/integration/test_repository_layout_contract.py`

- [ ] **Step 1: Write the failing distribution contract tests**

```python
def test_public_docs_cover_git_backed_uv_distribution(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    package_readme = (project_root / "README-package.md").read_text(encoding="utf-8")
    runbook = (project_root / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")

    assert "uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help" in readme
    assert "uv tool install git+https://github.com/momocloud/pizhi.git" in readme
    assert "uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help" in readme
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0" in readme
    assert "uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help" in package_readme
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0" in package_readme
    assert "Install the CLI with uv" in runbook
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0" in runbook


def test_distribution_metadata_contract(project_root):
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    contributing = (project_root / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert 'name = "pizhi"' in pyproject
    assert 'version = "0.1.0"' in pyproject
    assert 'readme = "README-package.md"' in pyproject
    assert 'pizhi = "pizhi.cli:main"' in pyproject
    assert "v0.1.0" in contributing
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- failures because the current docs do not yet advertise Git-backed `uvx` and `uv tool install`
- failure because `CONTRIBUTING.md` does not yet mention the `v0.1.0` tag convention

- [ ] **Step 3: Add the minimum contract assertions only**

Keep the tests limited to stable, user-facing promises:

- the four supported Git-backed `uv` command shapes
- the existing package metadata values
- the contributor-facing `v0.1.0` tag note

Do not assert transient wording, release automation, or PyPI behavior.

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- selected tests still fail because the docs have not been updated yet

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py
git commit -m "test: add uv git distribution contracts"
```

### Task 2: Update Public Docs For Git-Backed `uv` Consumption

**Files:**
- Modify: `README.md`
- Modify: `README-package.md`
- Modify: `docs/guides/getting-started.md`
- Modify: `tests/integration/test_docs_contract.py`

- [ ] **Step 1: Update the landing page and package readme**

Add concise, user-facing sections that document:

- `uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help`
- `uv tool install git+https://github.com/momocloud/pizhi.git`
- `uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help`
- `uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0`

Also explain:

- prefer `@v0.1.0` for automation and stable environments
- prefer untagged `main` only when intentionally following the latest branch tip

Keep `README-package.md` package-safe: no repository-relative links and no GitHub-only navigation assumptions.

- [ ] **Step 2: Update the getting-started guide**

Add a short acquisition section near the top:

````markdown
## Install the CLI with uv

```bash
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0
```
````

Then keep the rest of the runbook focused on normal `pizhi` usage after installation.

- [ ] **Step 3: Run the targeted docs tests**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- selected tests `PASSED`

- [ ] **Step 4: Run CLI help to confirm the packaged entry point is still valid**

Run:
`python -m pizhi --help`

Expected:
- help prints successfully

- [ ] **Step 5: Commit**

```bash
git add README.md README-package.md docs/guides/getting-started.md tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py
git commit -m "docs: add uv git distribution guidance"
```

### Task 3: Align Contributor And Release Notes With Tagged Git Distribution

**Files:**
- Modify: `CONTRIBUTING.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/integration/test_repository_layout_contract.py`

- [ ] **Step 1: Update contributor guidance**

Add a short section that explains:

- the first public stability tag for Git-backed installs is `v0.1.0`
- stable consumer examples should prefer `@v0.1.0`
- repository changes that alter install or packaging behavior must update the public docs and distribution contract tests

- [ ] **Step 2: Keep the changelog aligned with the public baseline**

If needed, add a concise unreleased note such as:

```markdown
- Document Git-backed `uvx` and `uv tool install` distribution from the public repository.
```

Do not invent historical release notes beyond the existing `v0.1.0` baseline.

- [ ] **Step 3: Run the targeted repository-contract tests**

Run:
`python -m pytest tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- selected tests `PASSED`

- [ ] **Step 4: Run focused docs/help regression**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py tests/integration/test_cli_help_contract.py -q --tb=short -rfE`

Expected:
- all selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add CONTRIBUTING.md CHANGELOG.md tests/integration/test_repository_layout_contract.py
git commit -m "docs: align contributor guidance for uv git installs"
```

### Task 4: Verify Full Regression And Record Release Handoff

**Files:**
- Modify: `meta/plans/2026-04-21-pizhi-uv-git-distribution.md`

- [ ] **Step 1: Run the full regression suite**

Run:
`python -m pytest tests/unit tests/integration -q --tb=short -rfE`

Expected:
- full suite `PASSED`

- [ ] **Step 2: Record the observed verification results in this plan**

Update the preflight or verification note if the final observed results differ from:

- `317 passed in 94.41s`

- [ ] **Step 3: Record the release handoff note**

Add a short note to this plan that final tagging must happen on merged `main`:

```markdown
Release handoff:
- After merging this branch to `main`, create tag `v0.1.0` on the merged `main` commit.
- Push `main` and `v0.1.0` to `origin` before running remote Git-backed `uv` smoke checks.
```

- [ ] **Step 4: Commit**

```bash
git add meta/plans/2026-04-21-pizhi-uv-git-distribution.md
git commit -m "docs: record uv git distribution verification"
```

- [ ] **Step 5: Post-merge release verification**

After this branch is merged to `main`, run these commands from the merged main checkout and confirm they succeed:

```bash
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0 --force
pizhi --help
```

Expected:
- the public GitHub repo resolves
- the `v0.1.0` tag is reachable remotely
- the installed `pizhi` entry point starts successfully

Execution notes:
- Observed verification result: `319 passed in 88.83s`
- Release handoff note: After merging this branch to `main`, create tag `v0.1.0` on the merged `main` commit.
- Push `main` and `v0.1.0` to `origin` before running remote Git-backed `uv` smoke checks.

## Notes

- Do not change CLI behavior while adding Git-backed `uv` distribution support; this milestone is documentation, metadata, testing, and release handoff only.
- Keep HTTPS Git URLs as the only documented public path for this milestone.
- Do not push `v0.1.0` from an unmerged feature branch; create and push the tag from merged `main`.
- Remote `uvx` and `uv tool install` smoke checks require the repository changes and tag to be pushed to `origin`.
