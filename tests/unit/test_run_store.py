from pizhi.services.run_store import RunStore


def test_run_store_persists_successful_run(tmp_path):
    store = RunStore(tmp_path / ".pizhi" / "cache" / "runs")
    record = store.write_success(
        command="write",
        target="ch001",
        prompt_text="# Prompt",
        raw_payload={"id": "resp_123"},
        normalized_text="## normalized\n",
        metadata={"provider": "openai_compatible"},
    )

    assert (record.run_dir / "manifest.json").exists()
    assert (record.run_dir / "raw.json").exists()
    assert (record.run_dir / "normalized.md").exists()


def test_run_store_persists_provider_failure_without_raw_or_normalized(tmp_path):
    store = RunStore(tmp_path / ".pizhi" / "cache" / "runs")
    record = store.write_failure(
        command="write",
        target="ch001",
        prompt_text="# Prompt",
        error_text="provider failed",
        metadata={"provider": "openai_compatible"},
    )

    assert (record.run_dir / "prompt.md").exists()
    assert (record.run_dir / "manifest.json").exists()
    assert (record.run_dir / "error.txt").exists()
    assert not (record.run_dir / "raw.json").exists()
    assert not (record.run_dir / "normalized.md").exists()


def test_run_store_persists_normalize_failure_with_raw_payload(tmp_path):
    store = RunStore(tmp_path / ".pizhi" / "cache" / "runs")
    record = store.write_failure(
        command="write",
        target="ch001",
        prompt_text="# Prompt",
        raw_payload={"id": "resp_123"},
        error_text="normalize failed",
        metadata={"provider": "openai_compatible"},
    )

    assert (record.run_dir / "prompt.md").exists()
    assert (record.run_dir / "manifest.json").exists()
    assert (record.run_dir / "raw.json").exists()
    assert (record.run_dir / "error.txt").exists()
    assert not (record.run_dir / "normalized.md").exists()
