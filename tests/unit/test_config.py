from pizhi.core.config import default_config, load_config, save_config


def test_config_round_trip(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)

    save_config(path, default_config(name="Test Novel"))

    loaded = load_config(path)
    assert loaded.project.name == "Test Novel"
    assert loaded.chapters.total_planned == 0
    assert loaded.consistency.checkpoint_interval == 3
