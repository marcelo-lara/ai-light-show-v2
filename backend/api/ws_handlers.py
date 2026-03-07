from __future__ import annotations

from typing import Any, Dict
import logging

from backend.api.intents.transport.router import handle_transport_intent
from backend.api.intents.fixture.router import handle_fixture_intent
from backend.api.intents.llm.router import handle_llm_intent

logger = logging.getLogger(__name__)

# Main intent dispatch map
INTENT_ROUTERS = {
    "transport": handle_transport_intent,
    "fixture": handle_fixture_intent,
    "llm": handle_llm_intent,
}

async def apply_intent(manager, name: str, payload: Dict[str, Any]) -> bool:
    """Processes frontend intents and updates state by delegating via a dispatch map."""
    manager._ensure_arm_state_initialized()

    # Split "domain.action" -> "domain"
    parts = name.split(".", 1)
    if len(parts) > 0:
        domain = parts[0]
        router = INTENT_ROUTERS.get(domain)
        if router:
            return await router(manager, name, payload)

    await manager.broadcast_event("warning", "unknown_intent", {"name": name})
    return False
