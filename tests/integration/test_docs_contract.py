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
    assert "The examples below use `python -m pizhi`, but the installed `pizhi` entry point is equivalent." in readme
    assert "Command examples use `python -m pizhi`, but the installed `pizhi` entry point is equivalent." in runbook
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
    assert "uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help" in package_readme
    assert "uv tool install git+https://github.com/momocloud/pizhi.git" in package_readme
    assert "uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help" in package_readme
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0" in package_readme
    assert "uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help" in runbook
    assert "uv tool install git+https://github.com/momocloud/pizhi.git" in runbook
    assert "uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help" in runbook
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0" in runbook
    caveat = (
        "Before the `v0.1.0` release tag is created on merged `main`, the untagged Git URL is the immediately valid install path. "
        "Once that tag exists, the `@v0.1.0` forms become the stable path for automation and pinned installs."
    )
    assert caveat in readme
    assert caveat in package_readme
    assert caveat in runbook


def test_readme_points_to_agent_playbook(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "](agents/pizhi/AGENTS.md)" in readme


def test_agent_playbook_markers_cover_execution_and_recovery_contract(project_root):
    agents_path = project_root / "agents" / "pizhi" / "AGENTS.md"
    recovery_path = project_root / "agents" / "pizhi" / "resources" / "failure-recovery.md"

    assert agents_path.exists(), f"Missing agent playbook: {agents_path}"
    assert recovery_path.exists(), f"Missing failure recovery guide: {recovery_path}"

    agents = agents_path.read_text(encoding="utf-8")
    recovery = recovery_path.read_text(encoding="utf-8")

    for marker in [
        "pizhi status",
        "pizhi continue run --count <n> --execute",
        "pizhi checkpoint apply --id <checkpoint_id>",
        "pizhi checkpoints --session-id <session_id>",
        "Do not edit `.pizhi/`",
    ]:
        assert marker in agents, f"Expected AGENTS.md to include marker: {marker!r}"

    for marker in [
        "provider not configured",
        "failed run",
        "checkpoint apply --id <checkpoint_id>",
        "v0.1.0",
    ]:
        assert marker in recovery, f"Expected failure-recovery.md to include marker: {marker!r}"
