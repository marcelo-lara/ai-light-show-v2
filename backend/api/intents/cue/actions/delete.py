from __future__ import annotations

from typing import Any, Dict


async def delete_cue(manager, payload: Dict[str, Any]) -> bool:
    """Delete a cue entry by index.

    Payload:
        index: int - cue entry index in the current cue array
    """
    index = payload.get("index")
    if index is None:
        await manager.broadcast_event("error", "cue_delete_failed", {"reason": "missing_index"})
        return False

    try:
        index_i = int(index)
    except (TypeError, ValueError):
        await manager.broadcast_event("error", "cue_delete_failed", {"reason": "invalid_index"})
        return False

    result = await manager.state_manager.delete_cue_entry(index_i)
    if not result.get("ok"):
        await manager.broadcast_event("error", "cue_delete_failed", result)
        return False

    await manager.broadcast_event("info", "cue_deleted", result)
    return True
