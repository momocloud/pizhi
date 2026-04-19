from pizhi.core.config import ProviderSection
from pizhi.core.config import default_config
from pizhi.core.config import load_config
from pizhi.core.config import save_config


def test_config_round_trip(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)

    config = default_config(name="Test Novel")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    save_config(path, config)

    loaded = load_config(path)
    assert loaded.project.name == "Test Novel"
    assert loaded.chapters.total_planned == 0
    assert loaded.consistency.checkpoint_interval == 3
    assert loaded.provider.model == "gpt-5.4"
    assert loaded.provider.api_key_env == "OPENAI_API_KEY"
