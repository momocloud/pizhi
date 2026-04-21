def test_public_docs_surface_excludes_internal_process_docs(project_root):
    assert (project_root / "docs" / "guides" / "getting-started.md").exists()
    assert (project_root / "docs" / "guides" / "recovery.md").exists()
    assert (project_root / "docs" / "architecture" / "ARCHITECTURE.md").exists()
    assert not (project_root / "docs" / "superpowers").exists()
    assert (project_root / "meta" / "specs").exists()
    assert (project_root / "meta" / "plans").exists()
    expected_meta_docs = [
        "meta/specs/2026-04-15-pizhi-core-design.md",
        "meta/specs/2026-04-16-pizhi-milestone-4-maintenance-design.md",
        "meta/specs/2026-04-18-pizhi-milestone-5-maintenance-closure-design.md",
        "meta/specs/2026-04-19-pizhi-milestone-6-provider-first-design.md",
        "meta/specs/2026-04-19-pizhi-milestone-7-provider-orchestration-design.md",
        "meta/specs/2026-04-19-pizhi-milestone-8-ai-review-design.md",
        "meta/specs/2026-04-20-pizhi-milestone-9-v1-closure-design.md",
        "meta/specs/2026-04-20-pizhi-milestone-10-delivery-and-extension-design.md",
        "meta/specs/2026-04-20-pizhi-open-source-repo-organization-design.md",
        "meta/plans/2026-04-15-pizhi-milestone-1-bootstrap.md",
        "meta/plans/2026-04-16-pizhi-milestone-2-engine.md",
        "meta/plans/2026-04-16-pizhi-milestone-3-orchestration.md",
        "meta/plans/2026-04-16-pizhi-milestone-4-maintenance.md",
        "meta/plans/2026-04-18-pizhi-milestone-5-maintenance-closure.md",
        "meta/plans/2026-04-19-pizhi-milestone-6-provider-first.md",
        "meta/plans/2026-04-19-pizhi-milestone-7-provider-orchestration.md",
        "meta/plans/2026-04-19-pizhi-milestone-8-ai-review.md",
        "meta/plans/2026-04-20-pizhi-milestone-9-v1-closure.md",
        "meta/plans/2026-04-20-pizhi-milestone-10-delivery-and-extension.md",
        "meta/plans/2026-04-20-pizhi-open-source-repo-organization.md",
    ]

    for relative in expected_meta_docs:
        assert (project_root / relative).exists(), relative


def test_repository_contains_expected_open_source_metadata(project_root):
    expected = [
        "README.md",
        "README-package.md",
        "ARCHITECTURE.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "CHANGELOG.md",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        ".github/pull_request_template.md",
        "meta/specs/2026-04-20-pizhi-open-source-repo-organization-design.md",
        "meta/plans/2026-04-15-pizhi-milestone-1-bootstrap.md",
    ]

    for relative in expected:
        assert (project_root / relative).exists(), relative


def test_pyproject_uses_readme_as_package_readme(project_root):
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'readme = "README-package.md"' in pyproject
    assert (project_root / "README-package.md").read_text(encoding="utf-8").startswith("# Pizhi")


def test_contributing_doc_mentions_setup_and_test_command(project_root):
    contributing = (project_root / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert 'python -m pip install -e ".[dev]"' in contributing
    assert "python -m pytest tests/unit tests/integration -q --tb=short -rfE" in contributing
    assert "meta/specs" in contributing
    assert "meta/plans" in contributing


def test_security_doc_mentions_private_reporting(project_root):
    security = (project_root / "SECURITY.md").read_text(encoding="utf-8")
    assert "Please do not report security issues through public GitHub issues." in security
    assert "GitHub Security Advisories" in security
    assert "repository owner's GitHub profile contact links" in security
    assert "owner or the maintainers responsible for security handling" in security
    assert "Security report: request private contact" in security


def test_code_of_conduct_mentions_private_enforcement_contact(project_root):
    code_of_conduct = (project_root / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")
    assert "reported privately through the maintainer contact channel documented in SECURITY.md" in code_of_conduct
    assert "minimal public issue fallback described there" in code_of_conduct
    assert "Community leaders are responsible for enforcement" in code_of_conduct


def test_visible_oss_artifacts_have_expected_markers(project_root):
    license_text = (project_root / "LICENSE").read_text(encoding="utf-8")
    changelog = (project_root / "CHANGELOG.md").read_text(encoding="utf-8")
    bug_template = (project_root / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").read_text(encoding="utf-8")
    feature_template = (project_root / ".github" / "ISSUE_TEMPLATE" / "feature_request.md").read_text(encoding="utf-8")

    assert "MIT License" in license_text
    assert "[Unreleased]" in changelog
    assert "v0.1.0" in changelog
    assert "## What happened?" in bug_template
    assert "## Steps to reproduce" in bug_template
    assert "security vulnerability" in bug_template
    assert "## Problem statement" in feature_template
    assert "## Proposed solution" in feature_template
    assert "security vulnerability" in feature_template


def test_distribution_metadata_contract(project_root):
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    contributing = (project_root / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert 'name = "pizhi"' in pyproject
    assert 'version = "0.1.0"' in pyproject
    assert 'pizhi = "pizhi.cli:main"' in pyproject
    normalized_contributing = contributing.replace("`", "").lower()
    assert "v0.1.0" in normalized_contributing
    assert "git" in normalized_contributing
    assert "uv" in normalized_contributing
