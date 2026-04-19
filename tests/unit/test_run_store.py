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


def test_run_store_round_trips_loaded_successful_run(tmp_path):
    store = RunStore(tmp_path / ".pizhi" / "cache" / "runs")
    record = store.write_success(
        command="write",
        target="ch001",
        prompt_text="# Prompt",
        raw_payload={"id": "resp_123"},
        normalized_text="## normalized\n",
        metadata={"provider": "openai_compatible", "model": "gpt-5.4", "base_url": "https://api.openai.com/v1"},
        referenced_files=[".pizhi/global/synopsis.md"],
    )

    loaded = store.load(record.run_id)

    assert loaded.run_id == record.run_id
    assert loaded.command == "write"
    assert loaded.target == "ch001"
    assert loaded.status == "succeeded"
    assert loaded.metadata == {
        "provider": "openai_compatible",
        "model": "gpt-5.4",
        "base_url": "https://api.openai.com/v1",
    }
    assert loaded.referenced_files == [".pizhi/global/synopsis.md"]
    assert loaded.manifest_path.exists()
    assert loaded.raw_path.exists()
    assert loaded.normalized_path.exists()


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


def test_run_store_lists_runs_newest_first(tmp_path):
    store = RunStore(tmp_path / ".pizhi" / "cache" / "runs")
    first = store.write_success(
        command="write",
        target="ch001",
        prompt_text="# Prompt 1",
        raw_payload={"id": "resp_1"},
        normalized_text="## normalized 1\n",
        metadata={"provider": "openai_compatible"},
    )
    second = store.write_success(
        command="write",
        target="ch002",
        prompt_text="# Prompt 2",
        raw_payload={"id": "resp_2"},
        normalized_text="## normalized 2\n",
        metadata={"provider": "openai_compatible"},
    )

    records = store.list_runs()

    assert [record.run_id for record in records] == [second.run_id, first.run_id]
