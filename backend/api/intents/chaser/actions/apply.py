from __future__ import annotations

from typing import Any, Dict


async def apply_chaser(manager, payload: Dict[str, Any]) -> bool:
    chaser_id = str(payload.get("chaser_id") or "").strip()
    if not chaser_id:
        await manager.broadcast_event("error", "chaser_apply_failed", {"reason": "missing_chaser_id"})
        return False

    start_time_ms = payload.get("start_time_ms", 0)
    repetitions = payload.get("repetitions")
    try:
        start_time_ms_f = max(0.0, float(start_time_ms))
        repetitions_i = 1 if repetitions is None else max(1, int(repetitions))
    except (TypeError, ValueError):
        await manager.broadcast_event("error", "chaser_apply_failed", {"reason": "invalid_payload"})
        return False

    result = await manager.state_manager.apply_chaser(chaser_id, start_time_ms_f, repetitions_i)
    if not result.get("ok"):
        await manager.broadcast_event("error", "chaser_apply_failed", result)
        return False

    await manager.broadcast_event("info", "chaser_applied", result)
    return True
