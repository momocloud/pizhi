def test_readme_runbook_and_recovery_content_contract(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    runbook = (project_root / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    recovery = (project_root / "docs" / "guides" / "recovery.md").read_text(encoding="utf-8")

    assert "pizhi init" in readme
    assert "pizhi continue run --count 3 --execute" in readme
    assert "pizhi checkpoints --session-id <session_id>" in readme
    assert "pizhi checkpoint apply --id <checkpoint_id>" in readme
    assert "pizhi continue resume --session-id <session_id>" in readme
    assert "Repeat checkpoint apply and resume until the continue session reaches `completed`" in readme
    assert "pizhi provider configure" in runbook
    assert "pizhi apply --run-id" in runbook
    assert "pizhi continue run --count <n> --execute" in runbook
    assert "pizhi review --chapter <n> --execute" in runbook
    assert "pizhi review --full --execute" in runbook
    assert "pizhi continue resume --session-id <session_id>" in runbook
    assert "pizhi checkpoint apply --id <checkpoint_id>" in runbook
    assert "Do not use `python -m pizhi apply --run-id <run_id>` for failed runs." in recovery
    assert "python -m pizhi continue resume --session-id <session_id>" in recovery


def test_readme_links_to_public_docs_and_governance_files(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "[Getting started](docs/guides/getting-started.md)" in readme
    assert "[Recovery guide](docs/guides/recovery.md)" in readme
    assert "[Architecture](docs/architecture/ARCHITECTURE.md)" in readme
    assert "[Contributing](CONTRIBUTING.md)" in readme
    assert "[Security](SECURITY.md)" in readme


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
    assert "uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help" in runbook
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0" in runbook
