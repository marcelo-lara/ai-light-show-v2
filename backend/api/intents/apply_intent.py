from __future__ import annotations

from typing import Any, Dict

from api.intents.registry import INTENT_HANDLERS


async def apply_intent(manager, name: str, payload: Dict[str, Any]) -> bool:
    manager._ensure_arm_state_initialized()
    domain = name.split(".", 1)[0] if name else ""
    handlers_by_domain = INTENT_HANDLERS.get(domain)
    if handlers_by_domain:
        handler = handlers_by_domain.get(name)
        if handler:
            return await handler(manager, payload)
    await manager.broadcast_event("warning", "unknown_intent", {"name": name})
    return False
