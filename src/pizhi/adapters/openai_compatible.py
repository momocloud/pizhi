from __future__ import annotations

from json import dumps
from typing import Any
from urllib.request import Request

from pizhi.adapters.provider_base import ProviderRequest
from pizhi.adapters.provider_base import ProviderResponse


def build_http_request(request: ProviderRequest) -> Request:
    payload = {
        "model": request.model,
        "messages": [{"role": "user", "content": request.prompt_text}],
    }
    return Request(
        f"{request.base_url.rstrip('/')}/chat/completions",
        data=dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {request.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )


def parse_response(payload: dict[str, Any]) -> ProviderResponse:
    return ProviderResponse(raw_payload=payload, content_text=extract_content_text(payload))


def extract_content_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(_extract_part_text(part) for part in content)
    return ""


def _extract_part_text(part: Any) -> str:
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        text = part.get("text")
        return text if isinstance(text, str) else ""
    return ""
