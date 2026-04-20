def test_readme_and_runbook_exist_and_reference_canonical_flow(project_root):
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
