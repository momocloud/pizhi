from __future__ import annotations

import json
from dataclasses import dataclass

from pizhi.adapters.provider_base import ProviderResponse
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.services.ai_review_context import AIReviewContext
from pizhi.services.ai_review_service import run_ai_review


NO_AI_REVIEW_ISSUES_MESSAGE = "- 未发现 B 类 AI 语义问题。\n"

VALID_AI_REVIEW_RESPONSE = """\
### 问题 1
- **描述**：沈轩前后动机冲突。
- **证据**：ch002 的动作与前文不一致。
- **类别**：人物一致性
- **建议修法**：补一段心理铺垫。
- **严重度**：高
"""

RAW_VALID_AI_REVIEW_RESPONSE = """\
### 问题 1
- **描述**：沈轩前后动机冲突。
- **证据**：ch002 的动作与前文不一致。
- **类别**：人物一致性
- **建议修法**：补一段心理铺垫。
- **严重度**：高
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


@dataclass
class StaticResponseAdapter:
    response: ProviderResponse
    captured: dict[str, object]

    def execute(self, provider_request):
        self.captured["provider_request"] = provider_request
        return self.response


@dataclass
class FailingAdapter:
    error_message: str

    def execute(self, provider_request):
        raise RuntimeError(self.error_message)


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


def test_run_ai_review_routes_through_review_command_family(initialized_project, monkeypatch):
    _configure_review_override(initialized_project)
    captured: dict[str, object] = {}

    class ExecutePromptStub:
        def __call__(self, project_root, request, target, provider_config=None, route_name=None):
            captured["project_root"] = project_root
            captured["request"] = request
            captured["target"] = target
            captured["provider_config"] = provider_config
            captured["route_name"] = route_name

            run_dir = project_root / ".pizhi" / "cache" / "runs" / "run-test"
            run_dir.mkdir(parents=True, exist_ok=True)
            normalized_path = run_dir / "normalized.md"
            normalized_path.write_text(NO_AI_REVIEW_ISSUES_MESSAGE, encoding="utf-8")
            error_path = run_dir / "error.txt"
            error_path.write_text("", encoding="utf-8")
            record = type(
                "RunRecordStub",
                (),
                {
                    "run_dir": run_dir,
                    "normalized_path": normalized_path,
                    "error_path": error_path,
                    "status": "succeeded",
                    "metadata": {},
                },
            )()
            return type(
                "ExecutionResultStub",
                (),
                {
                    "status": "succeeded",
                    "run_id": "run-test",
                    "record": record,
                },
            )()

    monkeypatch.setattr("pizhi.services.ai_review_service.execute_prompt_request", ExecutePromptStub())

    context = AIReviewContext(
        scope="chapter",
        target="ch002",
        prompt_context="...",
        referenced_files=[],
        metadata={},
    )

    result = run_ai_review(initialized_project, context)

    assert result.status == "succeeded"
    assert captured["route_name"] == "review"
    assert captured["target"] == "ch002"


def test_run_ai_review_falls_back_to_default_provider_config_when_review_override_missing(
    initialized_project, monkeypatch
):
    config_path = initialized_project / ".pizhi" / "config.yaml"
    config = load_config(config_path)
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    )
    save_config(config_path, config)

    captured: dict[str, object] = {}
    monkeypatch.setenv("OPENAI_API_KEY", "default-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StaticResponseAdapter(
            ProviderResponse(
                raw_payload={"id": "resp_test"},
                content_text=RAW_VALID_AI_REVIEW_RESPONSE,
            ),
            captured,
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

    provider_request = captured["provider_request"]
    assert result.status == "succeeded"
    assert provider_request.model == "gpt-5.4"
    assert provider_request.base_url == "https://api.openai.com/v1"
    assert provider_request.api_key == "default-secret"


def test_run_ai_review_returns_failed_provider_run_when_adapter_raises(
    initialized_project, monkeypatch
):
    _configure_review_override(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: FailingAdapter("provider request failed"),
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
    assert result.run_id is not None and result.run_id.startswith("run-")
    assert result.record is not None
    assert result.record.status == "provider_failed"
    assert result.error_message is not None
    assert "provider request failed" in result.error_message


def test_run_ai_review_returns_failed_normalize_run_when_adapter_returns_no_text(
    initialized_project, monkeypatch
):
    _configure_review_override(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StaticResponseAdapter(
            ProviderResponse(raw_payload={"id": "resp_test"}, content_text=""),
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
    assert result.run_id is not None and result.run_id.startswith("run-")
    assert result.record is not None
    assert result.record.status == "normalize_failed"
    assert result.record.normalized_path.exists()
    assert result.record.normalized_path.read_text(encoding="utf-8") == ""
    assert result.record.error_path.read_text(encoding="utf-8").strip() == "provider response did not contain text content"
    assert result.error_message is not None
    assert "provider response did not contain text content" in result.error_message


def test_run_ai_review_returns_succeeded_when_provider_reports_no_issues(
    initialized_project, monkeypatch
):
    _configure_review_override(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StaticResponseAdapter(
            ProviderResponse(raw_payload={"id": "resp_test"}, content_text=NO_AI_REVIEW_ISSUES_MESSAGE),
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

    assert result.status == "succeeded"
    assert result.issues == []
    assert result.rendered_markdown == NO_AI_REVIEW_ISSUES_MESSAGE


def test_run_ai_review_renders_canonical_markdown_after_parse(initialized_project, monkeypatch):
    _configure_review_override(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StaticResponseAdapter(
            ProviderResponse(raw_payload={"id": "resp_test"}, content_text=RAW_VALID_AI_REVIEW_RESPONSE),
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

    assert result.status == "succeeded"
    assert result.rendered_markdown != RAW_VALID_AI_REVIEW_RESPONSE
    assert result.rendered_markdown == (
        "### 问题 1\n"
        "- **类别**：人物一致性\n"
        "- **严重度**：高\n"
        "- **描述**：沈轩前后动机冲突。\n"
        "- **证据**：ch002 的动作与前文不一致。\n"
        "- **建议修法**：补一段心理铺垫。\n"
    )


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
    run_dir = result.record.run_dir
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

    assert result.status == "failed"
    assert result.run_id.startswith("run-")
    assert result.record is not None
    assert result.record.status == "failed"
    assert result.error_message is not None
    assert "unknown review category" in result.error_message
    assert manifest["status"] == "failed"
    assert (run_dir / "error.txt").exists()
    assert "unknown review category" in (run_dir / "error.txt").read_text(encoding="utf-8")
