from __future__ import annotations

from dataclasses import dataclass

from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.services.ai_review_context import AIReviewContext
from pizhi.services.ai_review_service import run_ai_review


VALID_AI_REVIEW_RESPONSE = """\
### 问题 1
- **类别**：人物一致性
- **严重度**：高
- **描述**：沈轩前后动机冲突。
- **证据**：ch002 的动作与前文不一致。
- **建议修法**：补一段心理铺垫。
"""


@dataclass
class RecordingAdapter:
    content_text: str
    captured: dict[str, object]

    def execute(self, provider_request):
        self.captured["provider_request"] = provider_request
        return type(
            "ProviderResponseStub",
            (),
            {
                "raw_payload": {"id": "resp_test"},
                "content_text": self.content_text,
            },
        )()


def _configure_review_override(initialized_project) -> None:
    config_path = initialized_project / ".pizhi" / "config.yaml"
    config = load_config(config_path)
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        review_model="gpt-5.4-mini",
        review_base_url="https://api.openai.com/v1/review",
        review_api_key_env="OPENAI_REVIEW_API_KEY",
    )
    save_config(config_path, config)


def test_run_ai_review_executes_with_review_provider_override(initialized_project, monkeypatch):
    _configure_review_override(initialized_project)
    captured: dict[str, object] = {}

    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RecordingAdapter(VALID_AI_REVIEW_RESPONSE, captured),
    )

    context = AIReviewContext(
        scope="chapter",
        target="ch002",
        prompt_context="...",
        referenced_files=[],
        metadata={},
    )

    result = run_ai_review(initialized_project, context)

    provider_request = captured["provider_request"]
    assert result.run_id.startswith("run-")
    assert result.record is not None
    assert result.record.metadata["model"] == "gpt-5.4-mini"
    assert result.issues[0].category == "人物一致性"
    assert provider_request.model == "gpt-5.4-mini"
    assert provider_request.base_url == "https://api.openai.com/v1/review"
    assert provider_request.api_key == "review-secret"


def test_run_ai_review_returns_failure_when_schema_is_invalid(initialized_project, monkeypatch):
    _configure_review_override(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RecordingAdapter(
            """\
### 问题 1
- **类别**：风格问题
- **严重度**：高
- **描述**：未列入白名单的类别。
- **证据**：示例。
- **建议修法**：示例。
""",
            {},
        ),
    )

    context = AIReviewContext(
        scope="chapter",
        target="ch002",
        prompt_context="...",
        referenced_files=[],
        metadata={},
    )

    result = run_ai_review(initialized_project, context)

    assert result.status == "failed"
    assert result.run_id.startswith("run-")
    assert result.error_message is not None
    assert "unknown review category" in result.error_message
