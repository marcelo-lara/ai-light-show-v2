from __future__ import annotations
from typing import Any, Dict

async def send_prompt(manager, payload: Dict[str, Any]) -> bool:
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        await manager.broadcast_event("error", "prompt_required")
        return False

    await manager.broadcast_event("info", "llm_stream", {
        "domain": "llm",
        "chunk": "Echo: ",
        "done": False,
    })
    await manager.broadcast_event("info", "llm_stream", {
        "domain": "llm",
        "chunk": prompt,
        "done": True,
    })
    return False

async def cancel(manager, payload: Dict[str, Any]) -> bool:
    await manager.broadcast_event("info", "llm_cancelled", {"domain": "llm"})
    return False

# Mapping of action names to functions
LLM_HANDLERS = {
    "llm.send_prompt": send_prompt,
    "llm.cancel": cancel,
}
