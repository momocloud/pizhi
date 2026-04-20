def test_readme_and_runbook_exist_and_reference_canonical_flow(project_root):
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    runbook = (project_root / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")

    assert "pizhi init" in readme
    assert "pizhi provider configure" in runbook
    assert "pizhi apply --run-id" in runbook
    assert "pizhi continue run --count <n> --execute" in runbook
    assert "pizhi review --chapter <n> --execute" in runbook
    assert "pizhi review --full --execute" in runbook
