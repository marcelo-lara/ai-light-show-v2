from __future__ import annotations

from typing import Any, Dict, Optional


async def clear_cue(manager, payload: Dict[str, Any]) -> bool:
    """Clear cue entries by time range.

    Payload:
        from_time: float (optional, defaults to 0.0)
        to_time: float (optional)
    """
    from_time = payload.get("from_time", 0.0)
    to_time_raw = payload.get("to_time")

    try:
        from_time_f = float(from_time)
    except (TypeError, ValueError):
        await manager.broadcast_event("error", "cue_clear_failed", {"reason": "invalid_from_time"})
        return False

    to_time_f: Optional[float]
    if to_time_raw is None:
        to_time_f = None
    else:
        try:
            to_time_f = float(to_time_raw)
        except (TypeError, ValueError):
            await manager.broadcast_event("error", "cue_clear_failed", {"reason": "invalid_to_time"})
            return False

    if to_time_f is not None and to_time_f < from_time_f:
        await manager.broadcast_event("error", "cue_clear_failed", {"reason": "invalid_time_range"})
        return False

    result = await manager.state_manager.clear_cue_entries(from_time=from_time_f, to_time=to_time_f)
    if not result.get("ok"):
        await manager.broadcast_event("error", "cue_clear_failed", result)
        return False

    await manager.broadcast_event("info", "cue_cleared", result)
    return True
