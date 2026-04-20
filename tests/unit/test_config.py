from pizhi.core.config import ProviderSection
from pizhi.core.config import default_config
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.paths import project_paths


def test_project_paths_runs_dir_uses_cache_subdir(tmp_path):
    paths = project_paths(tmp_path)

    assert paths.runs_dir == tmp_path.resolve() / ".pizhi" / "cache" / "runs"


def test_config_round_trip(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)

    config = default_config(name="Test Novel")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        brainstorm_model="gpt-5.4-brainstorm",
        outline_model="gpt-5.4-outline",
    )
    save_config(path, config)

    loaded = load_config(path)
    assert loaded.project.name == "Test Novel"
    assert loaded.chapters.total_planned == 0
    assert loaded.consistency.checkpoint_interval == 3
    assert loaded.provider.model == "gpt-5.4"
    assert loaded.provider.api_key_env == "OPENAI_API_KEY"
    assert loaded.provider.brainstorm_model == "gpt-5.4-brainstorm"
    assert loaded.provider.outline_model == "gpt-5.4-outline"


def test_config_round_trip_includes_review_provider_override(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)

    config = default_config(name="Test Novel")
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        write_model="gpt-5.4-write",
        continue_model="gpt-5.4-continue",
        review_model="gpt-5.4-mini",
        review_base_url="https://api.openai.com/v1",
        review_api_key_env="OPENAI_REVIEW_API_KEY",
    )
    save_config(path, config)

    loaded = load_config(path)
    assert loaded.provider is not None
    assert loaded.provider.write_model == "gpt-5.4-write"
    assert loaded.provider.continue_model == "gpt-5.4-continue"
    assert loaded.provider.review_model == "gpt-5.4-mini"
    assert loaded.provider.review_api_key_env == "OPENAI_REVIEW_API_KEY"


def test_provider_section_resolve_review_config_uses_override_values():
    provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        review_model="gpt-5.4-mini",
        review_base_url="https://api.openai.com/v1/review",
        review_api_key_env="OPENAI_REVIEW_API_KEY",
    )

    review_config = provider.resolve_review_config()

    assert review_config.provider == "openai_compatible"
    assert review_config.model == "gpt-5.4-mini"
    assert review_config.base_url == "https://api.openai.com/v1/review"
    assert review_config.api_key_env == "OPENAI_REVIEW_API_KEY"


def test_provider_section_resolve_route_config_uses_route_overrides_and_keeps_review_semantics():
    provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        brainstorm_model="gpt-5.4-brainstorm",
        outline_model="gpt-5.4-outline",
        write_model="gpt-5.4-write",
        continue_model="gpt-5.4-continue",
        review_model="gpt-5.4-mini",
        review_base_url="https://api.openai.com/v1/review",
        review_api_key_env="OPENAI_REVIEW_API_KEY",
    )

    brainstorm_config = provider.resolve_route_config("brainstorm")
    outline_config = provider.resolve_route_config("outline")
    write_config = provider.resolve_route_config("write")
    continue_config = provider.resolve_route_config("continue")
    review_config = provider.resolve_route_config("review")

    assert brainstorm_config.model == "gpt-5.4-brainstorm"
    assert outline_config.model == "gpt-5.4-outline"
    assert write_config.model == "gpt-5.4-write"
    assert continue_config.model == "gpt-5.4-continue"
    assert brainstorm_config.base_url == "https://api.openai.com/v1"
    assert brainstorm_config.api_key_env == "OPENAI_API_KEY"
    assert review_config == provider.resolve_review_config()


def test_config_loads_legacy_config_without_provider_block(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                "project:",
                "  name: Legacy Novel",
                "  genre: Crime Fiction",
                "  pov: Third Person Limited",
                "  created: '2026-04-19'",
                "  last_updated: '2026-04-19'",
                "chapters:",
                "  total_planned: 260",
                "  per_volume: 20",
                "generation:",
                "  context_window:",
                "    prev_chapters: 2",
                "    max_outline_words: 500",
                "    max_chapter_words: 5000",
                "  style:",
                "    tone: cinematic",
                "    dialogue_ratio: 0.35",
                "consistency:",
                "  auto_check: true",
                "  checkpoint_interval: 3",
                "foreshadowing:",
                "  auto_archive_resolved: true",
                "  reminder_threshold: 5",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_config(path)
    assert loaded.project.name == "Legacy Novel"
    assert loaded.provider is None


def test_save_config_omits_provider_block_when_missing(tmp_path):
    path = tmp_path / ".pizhi" / "config.yaml"
    path.parent.mkdir(parents=True)

    save_config(path, default_config(name="Test Novel"))

    saved_text = path.read_text(encoding="utf-8")
    assert "provider:" not in saved_text
