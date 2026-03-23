from __future__ import annotations

from typing import Any, Dict, List
import asyncio
from uuid import uuid4

from api.intents.llm.stream_runner import stream_prompt


def _normalize_history(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    raw_history = payload.get("history")
    if not isinstance(raw_history, list):
        return []

    normalized: List[Dict[str, str]] = []
    for item in raw_history:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        text = str(item.get("text") or "").strip()
        if role not in {"user", "assistant"} or not text:
            continue
        normalized.append({"role": role, "content": text})
    return normalized


async def send_prompt(manager, payload: Dict[str, Any]) -> bool:
    prompt = str(payload.get("prompt") or "").strip()
    history = _normalize_history(payload)
    if not prompt:
        await manager.broadcast_event("error", "prompt_required")
        return False

    if await manager.state_manager.get_is_playing():
        await manager.broadcast_event("warning", "llm_rejected", {"domain": "llm", "reason": "show_running"})
        return False

    await manager.cancel_llm_task()
    request_id = uuid4().hex
    task = asyncio.create_task(stream_prompt(manager, prompt, history))
    manager.track_llm_task(task, request_id)
    return False
