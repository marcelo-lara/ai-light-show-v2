from __future__ import annotations

from typing import Any, Dict


async def start_chaser(manager, payload: Dict[str, Any]) -> bool:
    chaser_name = str(payload.get("chaser_name") or "").strip()
    if not chaser_name:
        await manager.broadcast_event("error", "chaser_start_failed", {"reason": "missing_chaser_name"})
        return False

    start_time_ms = payload.get("start_time_ms", 0)
    repetitions = payload.get("repetitions")
    try:
        start_time_ms_f = max(0.0, float(start_time_ms))
        repetitions_i = 1 if repetitions is None else max(1, int(repetitions))
    except (TypeError, ValueError):
        await manager.broadcast_event("error", "chaser_start_failed", {"reason": "invalid_payload"})
        return False

    result = await manager.state_manager.start_chaser_instance(chaser_name, start_time_ms_f, repetitions_i)
    if not result.get("ok"):
        await manager.broadcast_event("error", "chaser_start_failed", result)
        return False

    await manager.broadcast_event("info", "chaser_started", result)
    return True
