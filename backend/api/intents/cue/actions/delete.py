from __future__ import annotations

from typing import Any, Dict

from api.intents.cue.mutate_rows import execute_delete_cue


async def delete_cue(manager, payload: Dict[str, Any]) -> bool:
    """Delete a cue entry by index.

    Payload:
        index: int - cue entry index in the current cue array
    """
    result = await execute_delete_cue(manager, payload)
    await manager.broadcast_event(result["level"], result["message"], result["data"])
    return result["ok"]
