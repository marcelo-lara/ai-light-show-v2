from __future__ import annotations

import json
from typing import Tuple


def parse_stream_line(line: str) -> Tuple[str, bool]:
    stripped = line.strip()
    if not stripped or not stripped.startswith("data:"):
        return "", False

    payload = stripped[5:].strip()
    if not payload:
        return "", False
    if payload == "[DONE]":
        return "", True

    message = json.loads(payload)
    choices = message.get("choices") or []
    if not choices:
        return "", False

    choice = choices[0] or {}
    delta = choice.get("delta") or {}
    content = delta.get("content")
    finished = choice.get("finish_reason") is not None
    return content if isinstance(content, str) else "", finished