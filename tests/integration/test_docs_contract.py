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

    assert readme.startswith("![Pizhi project header](docs/assets/pizhi-header.png)\n\n# Pizhi")
    assert "[Getting started](docs/guides/getting-started.md)" in readme
    assert "[Recovery guide](docs/guides/recovery.md)" in readme
    assert "[Architecture](docs/architecture/ARCHITECTURE.md)" in readme
    assert "[Chinese documentation archive](docs/zh/README.md)" in readme
    assert "[Contributing](CONTRIBUTING.md)" in readme
    assert "[Security](SECURITY.md)" in readme


def test_readme_surfaces_chinese_docs_link_near_top(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    top_readme = "\n".join(readme.splitlines()[:8])

    assert "[中文文档](docs/zh/README.md)" in top_readme


def test_default_public_docs_are_english_with_chinese_archive(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    getting_started = (project_root / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    recovery = (project_root / "docs" / "guides" / "recovery.md").read_text(encoding="utf-8")
    architecture = (project_root / "docs" / "architecture" / "ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "# Pizhi" in readme.splitlines()[:3]
    assert getting_started.startswith("# Getting Started")
    assert recovery.startswith("# Recovery Guide")
    assert architecture.startswith("# Pizhi Architecture")
    assert "[Chinese documentation archive](docs/zh/README.md)" in readme


def test_chinese_documentation_archive_tracks_public_docs(project_root):
    zh_readme = (project_root / "docs" / "zh" / "README.md").read_text(encoding="utf-8")
    zh_getting_started = (
        project_root / "docs" / "zh" / "guides" / "getting-started.md"
    ).read_text(encoding="utf-8")
    zh_recovery = (project_root / "docs" / "zh" / "guides" / "recovery.md").read_text(encoding="utf-8")
    zh_architecture = (
        project_root / "docs" / "zh" / "architecture" / "ARCHITECTURE.md"
    ).read_text(encoding="utf-8")

    assert "# Pizhi 中文文档归档" in zh_readme
    assert "LLM 辅助长篇小说创作工作流" in zh_readme
    assert "[开始使用](guides/getting-started.md)" in zh_readme
    assert "[恢复指南](guides/recovery.md)" in zh_readme
    assert "[架构](architecture/ARCHITECTURE.md)" in zh_readme
    assert "# 开始使用" in zh_getting_started
    assert "pizhi continue run --count <n> --execute" in zh_getting_started
    assert "# 恢复指南" in zh_recovery
    assert "不要对失败运行使用" in zh_recovery
    assert "# Pizhi 架构" in zh_architecture


def test_readme_documents_host_orchestrator_backend_split(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "Claude Code" in readme
    assert "Pizhi is the orchestrator" in readme
    assert "opencode" in readme
    assert "`--execute`" in readme


def test_public_docs_cover_git_backed_uv_distribution(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    package_readme = (project_root / "README-package.md").read_text(encoding="utf-8")
    runbook = (project_root / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")

    assert "uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help" in readme
    assert "uv tool install git+https://github.com/momocloud/pizhi.git" in readme
    assert "uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.1 pizhi --help" in readme
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.1" in readme
    assert "uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help" in package_readme
    assert "uv tool install git+https://github.com/momocloud/pizhi.git" in package_readme
    assert "uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.1 pizhi --help" in package_readme
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.1" in package_readme
    assert "uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help" in runbook
    assert "uv tool install git+https://github.com/momocloud/pizhi.git" in runbook
    assert "uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.1 pizhi --help" in runbook
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.1" in runbook
    caveat = "Use the untagged Git URL when you want the latest `main`. Prefer `@v0.1.1` for stable automation and pinned installs."
    assert caveat in readme
    assert caveat in package_readme
    assert caveat in runbook


def test_readme_points_to_agent_playbook(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "](agents/pizhi/AGENTS.md)" in readme


def test_agent_playbook_clarifies_external_host_vs_backend(project_root):
    agents_md = (project_root / "agents" / "pizhi" / "AGENTS.md").read_text(encoding="utf-8")

    assert "drive the `pizhi` CLI" in agents_md
    assert "opencode" in agents_md
    assert "Do not change provider configuration unless the user asked." in agents_md


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
        "Do not change provider configuration unless the user asked.",
    ]:
        assert marker in agents, f"Expected AGENTS.md to include marker: {marker!r}"

    for marker in [
        "provider not configured",
        "failed run",
        "checkpoint apply --id <checkpoint_id>",
        "v0.1.1",
        "If the session is waiting_apply, apply a checkpoint before resume.",
        "Do not use `pizhi apply --run-id <run_id>` for continue checkpoints.",
    ]:
        assert marker in recovery, f"Expected failure-recovery.md to include marker: {marker!r}"


def test_agent_playbook_resources_cover_run_apply_and_install_contract(project_root):
    agents = (project_root / "agents" / "pizhi" / "AGENTS.md").read_text(encoding="utf-8")
    workflow = (project_root / "agents" / "pizhi" / "resources" / "workflow.md").read_text(encoding="utf-8")
    commands = (project_root / "agents" / "pizhi" / "resources" / "commands.md").read_text(encoding="utf-8")
    examples = (project_root / "agents" / "pizhi" / "resources" / "examples.md").read_text(encoding="utf-8")
    recovery = (project_root / "agents" / "pizhi" / "resources" / "failure-recovery.md").read_text(encoding="utf-8")

    for marker in [
        "[workflow.md](resources/workflow.md)",
        "[commands.md](resources/commands.md)",
        "[failure-recovery.md](resources/failure-recovery.md)",
        "[examples.md](resources/examples.md)",
    ]:
        assert marker in agents, f"Expected AGENTS.md to link marker: {marker!r}"

    for marker in [
        "pizhi runs",
        "pizhi apply --run-id <run_id>",
    ]:
        assert marker in workflow, f"Expected workflow.md to include marker: {marker!r}"
        assert marker in commands, f"Expected commands.md to include marker: {marker!r}"

    assert "pizhi checkpoint apply --id <checkpoint_id>\npizhi continue resume --session-id <session_id>" in recovery

    assert "uv tool install git+https://github.com/momocloud/pizhi.git\n" in workflow
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.1" in workflow
    assert "`uvx` runs the CLI once without installing a reusable `pizhi` executable." in workflow
    assert "Use the untagged Git URL when you want the latest `main`. Prefer `@v0.1.1` for stable pinned installs." in workflow
    assert 'pizhi init --project-name "Example Novel"' in workflow
    assert "If the required execute backend configuration is missing, stop and ask before changing it." in workflow
    assert "pizhi init" in commands
    assert "pizhi provider configure" in commands
    assert "pizhi continue sessions" in commands
    assert "pizhi outline expand --chapters <a-b> --execute" in commands
    assert "pizhi write --chapter <n> --execute" in examples
    assert "pizhi runs" in examples
    assert "pizhi apply --run-id <run_id>" in examples
    assert "git+https://github.com/momocloud/pizhi.git" in examples
    assert "git+https://github.com/momocloud/pizhi.git@v0.1.1" in examples
    assert "uv tool install git+https://github.com/momocloud/pizhi.git\n" in examples
    assert "uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.1" in examples
    assert "`uvx` runs the CLI once without installing a reusable `pizhi` executable." in examples
    assert "pizhi provider configure --provider <provider> --model <model> --base-url <base_url> --api-key-env <env>" in examples
    assert "pizhi provider configure --provider <provider> --model <model> --base-url <base_url> --api-key-env <env>" in recovery
