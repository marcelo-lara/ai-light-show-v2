from __future__ import annotations

from typing import Any, Dict


async def add_cue(manager, payload: Dict[str, Any]) -> bool:
    """Add a single effect cue entry at the specified time.

    Payload:
        time: float — time in seconds
        fixture_id: str — target fixture id
        effect: str — effect name (must be supported by fixture)
        duration: float — effect duration in seconds
        data: dict — effect parameters
    """
    time = payload.get("time")
    fixture_id = str(payload.get("fixture_id") or "")
    effect = str(payload.get("effect") or "")
    duration = payload.get("duration", 0.0)
    data = payload.get("data") or {}

    if time is None:
        await manager.broadcast_event("error", "cue_add_failed", {"reason": "missing_time"})
        return False

    try:
        time_f = float(time)
    except (TypeError, ValueError):
        await manager.broadcast_event("error", "cue_add_failed", {"reason": "invalid_time"})
        return False

    if not fixture_id:
        await manager.broadcast_event("error", "cue_add_failed", {"reason": "missing_fixture_id"})
        return False

    if not effect:
        await manager.broadcast_event("error", "cue_add_failed", {"reason": "missing_effect"})
        return False

    try:
        duration_f = max(0.0, float(duration))
    except (TypeError, ValueError):
        duration_f = 0.0

    if not isinstance(data, dict):
        data = {}

    result = await manager.state_manager.add_effect_cue_entry(
        time=time_f,
        fixture_id=fixture_id,
        effect=effect,
        duration=duration_f,
        data=data,
    )

    if not result.get("ok"):
        await manager.broadcast_event("error", "cue_add_failed", result)
        return False

    await manager.broadcast_event("info", "cue_added", result)
    return True
