from subprocess import run
import sys

from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config


def test_provider_configure_command_supports_interactive_mode(initialized_project):
    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "provider",
            "configure",
        ],
        cwd=initialized_project,
        input="\n".join(
            [
                "openai_compatible",
                "gpt-5.4",
                "https://api.openai.com/v1",
                "OPENAI_API_KEY",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
        + "\n",
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Provider:" in result.stdout
    loaded = load_config(initialized_project / ".pizhi" / "config.yaml")
    assert loaded.provider is not None
    assert loaded.provider.provider == "openai_compatible"
    assert loaded.provider.model == "gpt-5.4"
    assert loaded.provider.base_url == "https://api.openai.com/v1"
    assert loaded.provider.api_key_env == "OPENAI_API_KEY"


def test_provider_configure_command_supports_interactive_review_override(initialized_project):
    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "provider",
            "configure",
        ],
        cwd=initialized_project,
        input="\n".join(
            [
                "openai_compatible",
                "gpt-5.4",
                "https://api.openai.com/v1",
                "OPENAI_API_KEY",
                "",
                "",
                "",
                "",
                "gpt-5.4-mini",
                "https://api.openai.com/v1",
                "OPENAI_REVIEW_API_KEY",
            ]
        )
        + "\n",
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Review model (leave blank to skip):" in result.stdout
    loaded = load_config(initialized_project / ".pizhi" / "config.yaml")
    assert loaded.provider is not None
    assert loaded.provider.review_model == "gpt-5.4-mini"
    assert loaded.provider.review_base_url == "https://api.openai.com/v1"
    assert loaded.provider.review_api_key_env == "OPENAI_REVIEW_API_KEY"


def test_provider_configure_command_writes_provider_block(initialized_project):
    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "provider",
            "configure",
            "--provider",
            "openai_compatible",
            "--model",
            "gpt-5.4",
            "--base-url",
            "https://api.openai.com/v1",
            "--api-key-env",
            "OPENAI_API_KEY",
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    loaded = load_config(initialized_project / ".pizhi" / "config.yaml")
    assert loaded.provider is not None
    assert loaded.provider.provider == "openai_compatible"
    assert loaded.provider.model == "gpt-5.4"
    assert loaded.provider.base_url == "https://api.openai.com/v1"
    assert loaded.provider.api_key_env == "OPENAI_API_KEY"


def test_provider_configure_command_writes_review_override_fields(initialized_project):
    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "provider",
            "configure",
            "--provider",
            "openai_compatible",
            "--model",
            "gpt-5.4",
            "--base-url",
            "https://api.openai.com/v1",
            "--api-key-env",
            "OPENAI_API_KEY",
            "--review-model",
            "gpt-5.4-mini",
            "--review-api-key-env",
            "OPENAI_REVIEW_API_KEY",
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    loaded = load_config(initialized_project / ".pizhi" / "config.yaml")
    assert loaded.provider is not None
    assert loaded.provider.review_model == "gpt-5.4-mini"


def test_provider_configure_command_writes_route_model_overrides(initialized_project):
    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "provider",
            "configure",
            "--provider",
            "openai_compatible",
            "--model",
            "gpt-5.4",
            "--base-url",
            "https://api.openai.com/v1",
            "--api-key-env",
            "OPENAI_API_KEY",
            "--brainstorm-model",
            "gpt-5.4-brainstorm",
            "--outline-model",
            "gpt-5.4-outline",
            "--write-model",
            "gpt-5.4-write",
            "--continue-model",
            "gpt-5.4-continue",
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    loaded = load_config(initialized_project / ".pizhi" / "config.yaml")
    assert loaded.provider is not None
    assert loaded.provider.brainstorm_model == "gpt-5.4-brainstorm"
    assert loaded.provider.outline_model == "gpt-5.4-outline"
    assert loaded.provider.write_model == "gpt-5.4-write"
    assert loaded.provider.continue_model == "gpt-5.4-continue"


def test_provider_configure_command_parameter_mode_preserves_existing_review_override(initialized_project):
    config_path = initialized_project / ".pizhi" / "config.yaml"
    config = load_config(config_path)
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="old-model",
        base_url="https://old.example/v1",
        api_key_env="OLD_API_KEY",
        review_model="gpt-5.4-mini",
        review_base_url="https://api.openai.com/v1/review",
        review_api_key_env="OPENAI_REVIEW_API_KEY",
    )
    save_config(config_path, config)

    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "provider",
            "configure",
            "--provider",
            "openai_compatible",
            "--model",
            "gpt-5.4",
            "--base-url",
            "https://api.openai.com/v1",
            "--api-key-env",
            "OPENAI_API_KEY",
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Review model" not in result.stdout
    loaded = load_config(config_path)
    assert loaded.provider is not None
    assert loaded.provider.review_model == "gpt-5.4-mini"
    assert loaded.provider.review_base_url == "https://api.openai.com/v1/review"
    assert loaded.provider.review_api_key_env == "OPENAI_REVIEW_API_KEY"
