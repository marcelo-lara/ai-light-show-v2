from __future__ import annotations

from typing import Any, Dict

from api.intents.cue.mutate_rows import execute_add_cue


async def add_cue(manager, payload: Dict[str, Any]) -> bool:
    """Add a single effect cue entry at the specified time.

    Payload:
        time: float — time in seconds
        fixture_id: str — target fixture id
        effect: str — effect name (must be supported by fixture)
        duration: float — effect duration in seconds
        data: dict — effect parameters
    """
    result = await execute_add_cue(manager, payload)
    await manager.broadcast_event(result["level"], result["message"], result["data"])
    return result["ok"]
