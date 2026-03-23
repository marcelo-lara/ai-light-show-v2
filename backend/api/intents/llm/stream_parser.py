from __future__ import annotations

import json
from typing import Any, Dict, Optional


def parse_stream_line(line: str) -> Optional[Dict[str, Any]]:
    stripped = line.strip()
    if not stripped or not stripped.startswith("data:"):
        return None

    payload = stripped[5:].strip()
    if not payload:
        return None
    if payload == "[DONE]":
        return {"type": "done"}

    message = json.loads(payload)

    event_type = message.get("type")
    if event_type == "status":
        status = message.get("status")
        if isinstance(status, str) and status.strip():
            return {"type": "status", "status": status}
        return None

    if event_type == "error":
        error = message.get("error")
        return {"type": "error", "error": error if isinstance(error, str) else "llm_stream_failed"}

    choices = message.get("choices") or []
    if not choices:
        return None

    choice = choices[0] or {}
    delta = choice.get("delta") or {}
    content = delta.get("content")
    finished = choice.get("finish_reason") is not None
    if isinstance(content, str) and content:
        return {"type": "content", "content": content, "done": finished}
    if finished:
        return {"type": "done"}
    return None