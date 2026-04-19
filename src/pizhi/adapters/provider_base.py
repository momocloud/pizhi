from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    model: str
    base_url: str
    api_key: str
    prompt_text: str


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    raw_payload: dict[str, Any]
    content_text: str
