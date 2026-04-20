def test_public_docs_surface_excludes_internal_process_docs(project_root):
    assert (project_root / "docs" / "guides" / "getting-started.md").exists()
    assert (project_root / "docs" / "guides" / "recovery.md").exists()
    assert (project_root / "docs" / "architecture" / "ARCHITECTURE.md").exists()
    assert not (project_root / "docs" / "superpowers").exists()
    assert (project_root / "meta" / "specs").exists()
    assert (project_root / "meta" / "plans").exists()
    expected_meta_docs = [
        "meta/specs/2026-04-15-pizhi-core-design.md",
        "meta/specs/2026-04-20-pizhi-open-source-repo-organization-design.md",
        "meta/plans/2026-04-15-pizhi-milestone-1-bootstrap.md",
        "meta/plans/2026-04-20-pizhi-milestone-10-delivery-and-extension.md",
        "meta/plans/2026-04-20-pizhi-open-source-repo-organization.md",
    ]

    for relative in expected_meta_docs:
        assert (project_root / relative).exists(), relative


def test_repository_contains_expected_open_source_metadata(project_root):
    expected = [
        "README.md",
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
    assert 'readme = "README.md"' in pyproject


def test_contributing_doc_mentions_setup_and_test_command(project_root):
    contributing = (project_root / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "python -m pip install -e ." in contributing
    assert "python -m pytest tests/unit tests/integration -q --tb=short -rfE" in contributing
    assert "meta/specs" in contributing
    assert "meta/plans" in contributing


def test_security_doc_mentions_private_reporting(project_root):
    security = (project_root / "SECURITY.md").read_text(encoding="utf-8")
    assert "Please do not report security issues through public GitHub issues." in security
