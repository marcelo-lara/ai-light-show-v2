from __future__ import annotations

from typing import Any, Dict
import asyncio
from uuid import uuid4

from api.intents.llm.stream_runner import stream_prompt


async def send_prompt(manager, payload: Dict[str, Any]) -> bool:
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        await manager.broadcast_event("error", "prompt_required")
        return False

    if await manager.state_manager.get_is_playing():
        await manager.broadcast_event("warning", "llm_rejected", {"domain": "llm", "reason": "show_running"})
        return False

    await manager.cancel_llm_task()
    request_id = uuid4().hex
    task = asyncio.create_task(stream_prompt(manager, prompt))
    manager.track_llm_task(task, request_id)
    return False
