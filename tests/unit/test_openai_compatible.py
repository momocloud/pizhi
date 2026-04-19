import json

from pizhi.adapters.openai_compatible import extract_content_text
from pizhi.adapters.openai_compatible import parse_response
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
    assert json.loads(prepared.data.decode("utf-8")) == {
        "model": "gpt-5.4",
        "messages": [{"role": "user", "content": "# Prompt"}],
    }


def test_openai_compatible_adapter_extracts_content_from_response():
    payload = {
        "choices": [
            {
                "message": {
                    "content": "## normalized\n",
                }
            }
        ]
    }

    response = parse_response(payload)

    assert response.raw_payload == payload
    assert response.content_text == "## normalized\n"
    assert extract_content_text(payload) == "## normalized\n"


def test_openai_compatible_adapter_returns_empty_text_when_choices_have_no_message_text():
    payload = {
        "choices": [
            {
                "message": {
                    "content": [{"type": "input_image", "image_url": "https://example.com/img.png"}],
                }
            }
        ]
    }

    response = parse_response(payload)

    assert response.raw_payload == payload
    assert response.content_text == ""
    assert extract_content_text(payload) == ""
