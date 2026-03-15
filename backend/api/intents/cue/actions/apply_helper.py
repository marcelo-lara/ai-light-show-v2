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

    if helper_id != "downbeats_and_beats":
        await manager.broadcast_event("error", "cue_helper_apply_failed", {"reason": "unknown_helper_id", "helper_id": helper_id})
        return False

    # Check if song has beats data
    if not manager.state_manager.current_song:
        await manager.broadcast_event("error", "cue_helper_apply_failed", {"reason": "no_song_loaded"})
        return False

    beats = manager.state_manager.current_song.beats
    if not beats or not beats.beats:
        await manager.broadcast_event("error", "cue_helper_apply_failed", {"reason": "beats_unavailable"})
        return False

    result = await manager.state_manager.apply_cue_helper(helper_id)
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