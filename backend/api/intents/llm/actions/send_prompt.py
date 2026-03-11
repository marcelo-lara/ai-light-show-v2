from __future__ import annotations

from typing import Any, Dict


async def send_prompt(manager, payload: Dict[str, Any]) -> bool:
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        await manager.broadcast_event("error", "prompt_required")
        return False
    await manager.broadcast_event("info", "llm_stream", {"domain": "llm", "chunk": "Echo: ", "done": False})
    await manager.broadcast_event("info", "llm_stream", {"domain": "llm", "chunk": prompt, "done": True})
    return False
