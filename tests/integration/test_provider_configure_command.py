from subprocess import run
import sys


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
    assert "provider:" in (initialized_project / ".pizhi" / "config.yaml").read_text(encoding="utf-8")
