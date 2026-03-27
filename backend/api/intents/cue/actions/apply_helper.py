from __future__ import annotations

from typing import Any, Dict


async def apply_helper(manager, payload: Dict[str, Any]) -> bool:
    """Apply a cue helper to generate cue entries.

    Payload:
        helper_id: str - ID of the helper to apply
    """
    helper_id = str(payload.get("helper_id") or "").strip()

    if not helper_id:
        await manager.broadcast_event("error", "cue_helper_apply_failed", {"reason": "missing_helper_id"})
        return False

    if not manager.state_manager.current_song:
        await manager.broadcast_event("error", "cue_helper_apply_failed", {"reason": "no_song_loaded"})
        return False

    raw_params = payload.get("params")
    params = {} if raw_params is None else raw_params
    if not isinstance(params, dict):
        await manager.broadcast_event("error", "cue_helper_apply_failed", {"reason": "invalid_helper_params", "helper_id": helper_id})
        return False

    result = await manager.state_manager.apply_cue_helper(helper_id, params)
    if not result.get("ok"):
        await manager.broadcast_event("error", "cue_helper_apply_failed", result)
        return False

    await manager.broadcast_event("info", "cue_helper_applied", {
        "helper_id": helper_id,
        "generated": result.get("generated", 0),
        "replaced": result.get("replaced", 0),
        "skipped": result.get("skipped", 0),
    })
    return True