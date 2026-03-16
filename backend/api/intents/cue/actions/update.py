from __future__ import annotations

from typing import Any, Dict


async def update_cue(manager, payload: Dict[str, Any]) -> bool:
    """Update an existing cue entry by index.

    Payload:
        index: int - cue entry index in the current cue array
        patch: dict - partial fields to update
    """
    index = payload.get("index")
    patch = payload.get("patch") or {}

    if index is None:
        await manager.broadcast_event("error", "cue_update_failed", {"reason": "missing_index"})
        return False

    try:
        index_i = int(index)
    except (TypeError, ValueError):
        await manager.broadcast_event("error", "cue_update_failed", {"reason": "invalid_index"})
        return False

    if not isinstance(patch, dict) or not patch:
        await manager.broadcast_event("error", "cue_update_failed", {"reason": "missing_patch"})
        return False

    result = await manager.state_manager.update_cue_entry(index_i, patch)
    if not result.get("ok"):
        await manager.broadcast_event("error", "cue_update_failed", result)
        return False

    await manager.broadcast_event("info", "cue_updated", result)
    return True
