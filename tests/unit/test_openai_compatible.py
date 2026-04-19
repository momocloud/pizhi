from pizhi.adapters.openai_compatible import ProviderRequest
from pizhi.adapters.openai_compatible import build_http_request


def test_openai_compatible_adapter_builds_chat_completions_request():
    request = ProviderRequest(
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key="secret",
        prompt_text="# Prompt",
    )

    prepared = build_http_request(request)

    assert prepared.full_url == "https://api.openai.com/v1/chat/completions"
    assert prepared.headers["Authorization"] == "Bearer secret"
