# Pizhi Open Source Repository Organization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repackage the repository into a conventional GitHub open-source layout by separating public docs from internal process docs, adding standard metadata files, and aligning package metadata and documentation entry points without changing product behavior.

**Architecture:** Keep the stable application layout under `src/` and `tests/`, preserve the canonical public docs under `docs/architecture/` and `docs/guides/`, and move milestone specs/plans into a root-level `meta/` tree. Add repository-contract tests so the new layout, governance files, and README/package metadata stay aligned after the move.

**Tech Stack:** Python 3.14, pytest, pathlib, existing CLI/help contracts, Markdown documentation, GitHub community file conventions

---

## Preflight

- Worktree: `C:\Users\kywin\ownProject\noval\Pizhi\.worktrees\repo-open-source-organization`
- Install editable package in the worktree before running tests:
  - `python -m pip install -e .`
- Clean baseline:
  - `python -m pytest tests/unit tests/integration -q --tb=short -rfE`
  - Observed while writing this plan: `309 passed in 100.60s`

## File Map

- `README.md`: keep as the single public landing page; add links to contribution and security docs if needed
- `ARCHITECTURE.md`: keep as a thin compatibility pointer to `docs/architecture/ARCHITECTURE.md`
- `pyproject.toml`: point package metadata `readme` at `README.md`
- `LICENSE`: add the MIT license text
- `CONTRIBUTING.md`: add local setup, test, PR, and documentation placement guidance
- `CODE_OF_CONDUCT.md`: add a standard contributor conduct document
- `SECURITY.md`: add a lightweight security-reporting policy suitable for a public repo
- `CHANGELOG.md`: add an initial changelog shell for future releases
- `.github/ISSUE_TEMPLATE/bug_report.md`: add a bug report template
- `.github/ISSUE_TEMPLATE/feature_request.md`: add a feature request template
- `.github/pull_request_template.md`: add a PR template
- `docs/architecture/ARCHITECTURE.md`: keep canonical architecture path unchanged and update references only if needed
- `docs/guides/getting-started.md`: keep public runbook path unchanged and update references only if needed
- `docs/guides/recovery.md`: keep public recovery-guide path unchanged and update references only if needed
- `meta/specs/2026-04-20-pizhi-open-source-repo-organization-design.md`: existing design doc; leave in place
- `meta/plans/2026-04-20-pizhi-open-source-repo-organization.md`: this plan; update verification notes if execution changes the observed results
- `meta/specs/2026-04-15-pizhi-core-design.md`: move from `docs/superpowers/specs/`
- `meta/specs/2026-04-16-pizhi-milestone-4-maintenance-design.md`: move from `docs/superpowers/specs/`
- `meta/specs/2026-04-18-pizhi-milestone-5-maintenance-closure-design.md`: move from `docs/superpowers/specs/`
- `meta/specs/2026-04-19-pizhi-milestone-6-provider-first-design.md`: move from `docs/superpowers/specs/`
- `meta/specs/2026-04-19-pizhi-milestone-7-provider-orchestration-design.md`: move from `docs/superpowers/specs/`
- `meta/specs/2026-04-19-pizhi-milestone-8-ai-review-design.md`: move from `docs/superpowers/specs/`
- `meta/specs/2026-04-20-pizhi-milestone-9-v1-closure-design.md`: move from `docs/superpowers/specs/`
- `meta/specs/2026-04-20-pizhi-milestone-10-delivery-and-extension-design.md`: move from `docs/superpowers/specs/`
- `meta/plans/2026-04-15-pizhi-milestone-1-bootstrap.md`: move from `docs/superpowers/plans/`
- `meta/plans/2026-04-16-pizhi-milestone-2-engine.md`: move from `docs/superpowers/plans/`
- `meta/plans/2026-04-16-pizhi-milestone-3-orchestration.md`: move from `docs/superpowers/plans/`
- `meta/plans/2026-04-16-pizhi-milestone-4-maintenance.md`: move from `docs/superpowers/plans/`
- `meta/plans/2026-04-18-pizhi-milestone-5-maintenance-closure.md`: move from `docs/superpowers/plans/`
- `meta/plans/2026-04-19-pizhi-milestone-6-provider-first.md`: move from `docs/superpowers/plans/`
- `meta/plans/2026-04-19-pizhi-milestone-7-provider-orchestration.md`: move from `docs/superpowers/plans/`
- `meta/plans/2026-04-19-pizhi-milestone-8-ai-review.md`: move from `docs/superpowers/plans/`
- `meta/plans/2026-04-20-pizhi-milestone-9-v1-closure.md`: move from `docs/superpowers/plans/`
- `meta/plans/2026-04-20-pizhi-milestone-10-delivery-and-extension.md`: move from `docs/superpowers/plans/`
- `tests/integration/test_docs_contract.py`: extend public-doc checks so they assert the intended public surface after the move
- `tests/integration/test_repository_layout_contract.py`: add repository-layout and metadata-file assertions for the open-source shape

### Task 1: Add Repository Layout Contract Tests

**Files:**
- Modify: `tests/integration/test_docs_contract.py`
- Create: `tests/integration/test_repository_layout_contract.py`

- [ ] **Step 1: Write the failing repository-layout tests**

```python
def test_public_docs_surface_excludes_internal_process_docs(project_root):
    assert (project_root / "docs" / "guides" / "getting-started.md").exists()
    assert (project_root / "docs" / "guides" / "recovery.md").exists()
    assert (project_root / "docs" / "architecture" / "ARCHITECTURE.md").exists()
    assert not (project_root / "docs" / "superpowers").exists()


def test_repository_contains_expected_open_source_metadata(project_root):
    expected = [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "CHANGELOG.md",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        ".github/pull_request_template.md",
        "meta/specs/2026-04-20-pizhi-open-source-repo-organization-design.md",
    ]

    for relative in expected:
        assert (project_root / relative).exists(), relative


def test_pyproject_uses_readme_as_package_readme(project_root):
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'readme = "README.md"' in pyproject
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- failures because `docs/superpowers/` still exists
- failures because repository metadata files and GitHub templates do not exist
- failure because `pyproject.toml` still points at `ARCHITECTURE.md`

- [ ] **Step 3: Implement the minimum repository-contract changes**

```python
def test_public_docs_surface_excludes_internal_process_docs(project_root):
    assert not (project_root / "docs" / "superpowers").exists()
    assert (project_root / "meta" / "specs").exists()
    assert (project_root / "meta" / "plans").exists()
```

Create the empty directory/file scaffolding needed for the new contract:

- `meta/specs/`
- `meta/plans/`
- `.github/ISSUE_TEMPLATE/`
- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `CHANGELOG.md`

and update `pyproject.toml` to use `README.md`.

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected: selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py LICENSE CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md CHANGELOG.md .github/ISSUE_TEMPLATE/bug_report.md .github/ISSUE_TEMPLATE/feature_request.md .github/pull_request_template.md
git commit -m "test: add open source repository layout contracts"
```

### Task 2: Move Internal Specs And Plans Into `meta/`

**Files:**
- Create: `meta/specs/2026-04-15-pizhi-core-design.md`
- Create: `meta/specs/2026-04-16-pizhi-milestone-4-maintenance-design.md`
- Create: `meta/specs/2026-04-18-pizhi-milestone-5-maintenance-closure-design.md`
- Create: `meta/specs/2026-04-19-pizhi-milestone-6-provider-first-design.md`
- Create: `meta/specs/2026-04-19-pizhi-milestone-7-provider-orchestration-design.md`
- Create: `meta/specs/2026-04-19-pizhi-milestone-8-ai-review-design.md`
- Create: `meta/specs/2026-04-20-pizhi-milestone-9-v1-closure-design.md`
- Create: `meta/specs/2026-04-20-pizhi-milestone-10-delivery-and-extension-design.md`
- Create: `meta/plans/2026-04-15-pizhi-milestone-1-bootstrap.md`
- Create: `meta/plans/2026-04-16-pizhi-milestone-2-engine.md`
- Create: `meta/plans/2026-04-16-pizhi-milestone-3-orchestration.md`
- Create: `meta/plans/2026-04-16-pizhi-milestone-4-maintenance.md`
- Create: `meta/plans/2026-04-18-pizhi-milestone-5-maintenance-closure.md`
- Create: `meta/plans/2026-04-19-pizhi-milestone-6-provider-first.md`
- Create: `meta/plans/2026-04-19-pizhi-milestone-7-provider-orchestration.md`
- Create: `meta/plans/2026-04-19-pizhi-milestone-8-ai-review.md`
- Create: `meta/plans/2026-04-20-pizhi-milestone-9-v1-closure.md`
- Create: `meta/plans/2026-04-20-pizhi-milestone-10-delivery-and-extension.md`
- Delete: `docs/superpowers/specs/2026-04-15-pizhi-core-design.md`
- Delete: `docs/superpowers/specs/2026-04-16-pizhi-milestone-4-maintenance-design.md`
- Delete: `docs/superpowers/specs/2026-04-18-pizhi-milestone-5-maintenance-closure-design.md`
- Delete: `docs/superpowers/specs/2026-04-19-pizhi-milestone-6-provider-first-design.md`
- Delete: `docs/superpowers/specs/2026-04-19-pizhi-milestone-7-provider-orchestration-design.md`
- Delete: `docs/superpowers/specs/2026-04-19-pizhi-milestone-8-ai-review-design.md`
- Delete: `docs/superpowers/specs/2026-04-20-pizhi-milestone-9-v1-closure-design.md`
- Delete: `docs/superpowers/specs/2026-04-20-pizhi-milestone-10-delivery-and-extension-design.md`
- Delete: `docs/superpowers/plans/2026-04-15-pizhi-milestone-1-bootstrap.md`
- Delete: `docs/superpowers/plans/2026-04-16-pizhi-milestone-2-engine.md`
- Delete: `docs/superpowers/plans/2026-04-16-pizhi-milestone-3-orchestration.md`
- Delete: `docs/superpowers/plans/2026-04-16-pizhi-milestone-4-maintenance.md`
- Delete: `docs/superpowers/plans/2026-04-18-pizhi-milestone-5-maintenance-closure.md`
- Delete: `docs/superpowers/plans/2026-04-19-pizhi-milestone-6-provider-first.md`
- Delete: `docs/superpowers/plans/2026-04-19-pizhi-milestone-7-provider-orchestration.md`
- Delete: `docs/superpowers/plans/2026-04-19-pizhi-milestone-8-ai-review.md`
- Delete: `docs/superpowers/plans/2026-04-20-pizhi-milestone-9-v1-closure.md`
- Delete: `docs/superpowers/plans/2026-04-20-pizhi-milestone-10-delivery-and-extension.md`

- [ ] **Step 1: Write the failing move/link tests**

```python
def test_internal_process_docs_live_under_meta(project_root):
    assert (project_root / "meta" / "specs" / "2026-04-15-pizhi-core-design.md").exists()
    assert (project_root / "meta" / "plans" / "2026-04-20-pizhi-milestone-10-delivery-and-extension.md").exists()
    assert not (project_root / "docs" / "superpowers" / "specs").exists()
    assert not (project_root / "docs" / "superpowers" / "plans").exists()
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- failure because the milestone docs are still under `docs/superpowers/`

- [ ] **Step 3: Move the files and update internal references**

Use repository-native file moves so Git preserves history.

Update any references that still mention:

- `docs/superpowers/specs/`
- `docs/superpowers/plans/`

to:

- `meta/specs/`
- `meta/plans/`

After the last file move, remove the now-empty `docs/superpowers/` tree.

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected: selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add meta/specs meta/plans docs/superpowers tests/integration/test_repository_layout_contract.py
git commit -m "docs: move internal process docs under meta"
```

### Task 3: Refresh Public Docs Surface And Package Entry Points

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `docs/architecture/ARCHITECTURE.md`
- Modify: `docs/guides/getting-started.md`
- Modify: `docs/guides/recovery.md`
- Modify: `tests/integration/test_docs_contract.py`
- Modify: `tests/integration/test_repository_layout_contract.py`

- [ ] **Step 1: Write the failing public-doc navigation tests**

```python
def test_readme_links_to_public_docs_and_governance_files(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "[Getting started](docs/guides/getting-started.md)" in readme
    assert "[Recovery guide](docs/guides/recovery.md)" in readme
    assert "[Architecture](docs/architecture/ARCHITECTURE.md)" in readme
    assert "[Contributing](CONTRIBUTING.md)" in readme
    assert "[Security](SECURITY.md)" in readme
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- failure because `README.md` does not yet link to the new governance files
- possible failures if moved-doc references still point at old paths

- [ ] **Step 3: Update the public docs and link surface**

Keep public docs intentionally small:

- `README.md` stays the public landing page
- `ARCHITECTURE.md` stays a thin pointer
- `docs/architecture/ARCHITECTURE.md` remains canonical architecture
- `docs/guides/getting-started.md` remains the canonical runbook
- `docs/guides/recovery.md` remains the canonical recovery guide

Only update wording and links needed to reflect the open-source layout and contributor/security entry points.

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected: selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add README.md ARCHITECTURE.md docs/architecture/ARCHITECTURE.md docs/guides/getting-started.md docs/guides/recovery.md tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py
git commit -m "docs: polish public repository navigation"
```

### Task 4: Add GitHub Community Files And Template Content

**Files:**
- Modify: `LICENSE`
- Modify: `CONTRIBUTING.md`
- Modify: `CODE_OF_CONDUCT.md`
- Modify: `SECURITY.md`
- Modify: `CHANGELOG.md`
- Modify: `.github/ISSUE_TEMPLATE/bug_report.md`
- Modify: `.github/ISSUE_TEMPLATE/feature_request.md`
- Modify: `.github/pull_request_template.md`
- Modify: `tests/integration/test_repository_layout_contract.py`

- [ ] **Step 1: Write the failing content-level tests**

```python
def test_contributing_doc_mentions_setup_and_test_command(project_root):
    contributing = (project_root / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "python -m pip install -e ." in contributing
    assert "python -m pytest tests/unit tests/integration -q --tb=short -rfE" in contributing
    assert "meta/specs" in contributing
    assert "meta/plans" in contributing


def test_security_doc_mentions_private_reporting(project_root):
    security = (project_root / "SECURITY.md").read_text(encoding="utf-8")
    assert "Please do not report security issues through public GitHub issues." in security
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`python -m pytest tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected:
- failure because the new community files and templates are placeholders or incomplete

- [ ] **Step 3: Write the repository metadata and template content**

Use standard, concise open-source wording:

- `LICENSE`: MIT text
- `CONTRIBUTING.md`: setup, tests, PR expectations, docs-placement rules
- `CODE_OF_CONDUCT.md`: Contributor Covenant text
- `SECURITY.md`: private-reporting guidance with a project-maintainer contact placeholder
- `CHANGELOG.md`: Keep a simple unreleased section and v1 baseline note
- GitHub templates: concise prompts aligned to this repo

- [ ] **Step 4: Run the targeted tests again**

Run:
`python -m pytest tests/integration/test_repository_layout_contract.py -q --tb=short -rfE`

Expected: selected tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add LICENSE CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md CHANGELOG.md .github/ISSUE_TEMPLATE/bug_report.md .github/ISSUE_TEMPLATE/feature_request.md .github/pull_request_template.md tests/integration/test_repository_layout_contract.py
git commit -m "docs: add open source community files"
```

### Task 5: Verify CLI Metadata And Full Repository Regression

**Files:**
- Modify: `meta/plans/2026-04-20-pizhi-open-source-repo-organization.md`

- [ ] **Step 1: Run CLI/help verification**

Run:
`python -m pizhi --help`

Expected:
- command help prints successfully

- [ ] **Step 2: Run the focused integration contract tests**

Run:
`python -m pytest tests/integration/test_docs_contract.py tests/integration/test_repository_layout_contract.py tests/integration/test_cli_help_contract.py -q --tb=short -rfE`

Expected:
- all selected tests `PASSED`

- [ ] **Step 3: Run the full regression suite**

Run:
`python -m pytest tests/unit tests/integration -q --tb=short -rfE`

Expected:
- full suite `PASSED`

- [ ] **Step 4: Update the plan with observed verification notes if outputs changed**

Record the final observed command results in this plan if they differ from the preflight section.

- [ ] **Step 5: Commit**

```bash
git add meta/plans/2026-04-20-pizhi-open-source-repo-organization.md
git commit -m "docs: record repository organization verification"
```

## Notes

- Keep the root `ARCHITECTURE.md` as a pointer file; do not duplicate the full architecture text there.
- Do not change CLI behavior while reorganizing docs and metadata.
- Prefer Git-aware moves for the milestone docs so history remains readable.
- The repository currently has no `.github/` directory, so create it only with the files required by this plan.
