from __future__ import annotations
from typing import Any, Dict
from api.intents.transport.handlers import TRANSPORT_HANDLERS

async def handle_transport_intent(manager, name: str, payload: Dict[str, Any]) -> bool:
    handler = TRANSPORT_HANDLERS.get(name)
    if handler:
        return await handler(manager, payload)
    return False
