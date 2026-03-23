from __future__ import annotations

from typing import Any, Dict

from api.intents.cue.mutate_rows import execute_update_cue


async def update_cue(manager, payload: Dict[str, Any]) -> bool:
    """Update an existing cue entry by index.

    Payload:
        index: int - cue entry index in the current cue array
        patch: dict - partial fields to update
    """
    result = await execute_update_cue(manager, payload)
    await manager.broadcast_event(result["level"], result["message"], result["data"])
    return result["ok"]
