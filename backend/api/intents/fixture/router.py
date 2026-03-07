from __future__ import annotations
from typing import Any, Dict
from api.intents.fixture.handlers import FIXTURE_HANDLERS

async def handle_fixture_intent(manager, name: str, payload: Dict[str, Any]) -> bool:
    handler = FIXTURE_HANDLERS.get(name)
    if handler:
        return await handler(manager, payload)
    return False
