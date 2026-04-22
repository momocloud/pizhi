from __future__ import annotations

from pizhi.services.chapter_parser import parse_chapter_response


def validate_write_candidate(raw_response: str) -> None:
    try:
        parse_chapter_response(raw_response)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"write candidate failed validation: {exc}") from exc
