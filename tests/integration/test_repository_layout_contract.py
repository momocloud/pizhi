def test_public_docs_surface_excludes_internal_process_docs(project_root):
    assert (project_root / "docs" / "guides" / "getting-started.md").exists()
    assert (project_root / "docs" / "guides" / "recovery.md").exists()
    assert (project_root / "docs" / "architecture" / "ARCHITECTURE.md").exists()
    assert not (project_root / "docs" / "superpowers").exists()
    assert (project_root / "meta" / "plans").exists()
    assert (project_root / "meta" / "plans" / "2026-04-15-pizhi-milestone-1-bootstrap.md").exists()


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
        "meta/plans/2026-04-15-pizhi-milestone-1-bootstrap.md",
    ]

    for relative in expected:
        assert (project_root / relative).exists(), relative


def test_pyproject_uses_readme_as_package_readme(project_root):
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'readme = "README.md"' in pyproject
