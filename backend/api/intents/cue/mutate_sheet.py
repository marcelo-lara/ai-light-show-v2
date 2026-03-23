from __future__ import annotations

from typing import Any, Dict, Optional


def _result(ok: bool, level: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": ok, "level": level, "message": message, "data": data}


async def execute_clear_cue(manager, payload: Dict[str, Any]) -> Dict[str, Any]:
    from_time = payload.get("from_time", 0.0)
    to_time_raw = payload.get("to_time")
    try:
        from_time_f = float(from_time)
    except (TypeError, ValueError):
        return _result(False, "error", "cue_clear_failed", {"reason": "invalid_from_time"})
    to_time_f: Optional[float] = None
    if to_time_raw is not None:
        try:
            to_time_f = float(to_time_raw)
        except (TypeError, ValueError):
            return _result(False, "error", "cue_clear_failed", {"reason": "invalid_to_time"})
    if to_time_f is not None and to_time_f < from_time_f:
        return _result(False, "error", "cue_clear_failed", {"reason": "invalid_time_range"})
    result = await manager.state_manager.clear_cue_entries(from_time=from_time_f, to_time=to_time_f)
    return _result(bool(result.get("ok")), "info" if result.get("ok") else "error", "cue_cleared" if result.get("ok") else "cue_clear_failed", result)


async def execute_apply_helper(manager, payload: Dict[str, Any]) -> Dict[str, Any]:
    helper_id = str(payload.get("helper_id") or "").strip()
    if not helper_id:
        return _result(False, "error", "cue_helper_apply_failed", {"reason": "missing_helper_id"})
    if helper_id != "downbeats_and_beats":
        return _result(False, "error", "cue_helper_apply_failed", {"reason": "unknown_helper_id", "helper_id": helper_id})
    current_song = manager.state_manager.current_song
    beats = getattr(current_song, "beats", None)
    if not current_song:
        return _result(False, "error", "cue_helper_apply_failed", {"reason": "no_song_loaded"})
    if not beats or not getattr(beats, "beats", None):
        return _result(False, "error", "cue_helper_apply_failed", {"reason": "beats_unavailable"})
    result = await manager.state_manager.apply_cue_helper(helper_id)
    if not result.get("ok"):
        return _result(False, "error", "cue_helper_apply_failed", result)
    data = {
        "helper_id": helper_id,
        "generated": result.get("generated", 0),
        "replaced": result.get("replaced", 0),
        "skipped": result.get("skipped", 0),
    }
    return _result(True, "info", "cue_helper_applied", data)