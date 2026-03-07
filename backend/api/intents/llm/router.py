from __future__ import annotations
from typing import Any, Dict
from backend.api.intents.llm.actions import LLM_HANDLERS

async def handle_llm_intent(manager, name: str, payload: Dict[str, Any]) -> bool:
    handler = LLM_HANDLERS.get(name)
    if handler:
        return await handler(manager, payload)
    return False
