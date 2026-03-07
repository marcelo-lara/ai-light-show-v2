from __future__ import annotations

from typing import Any, Dict


async def preview_effect(manager, payload: Dict[str, Any]) -> bool:
    fixture_id = str(payload.get("fixture_id") or "")
    effect = str(payload.get("effect_id") or "")
    duration_ms = payload.get("duration_ms")
    params = payload.get("params") or {}
    try:
        duration = max(0.0, float(str(duration_ms)) / 1000.0)
    except Exception:
        duration = 0.5

    result = await manager.state_manager.start_preview_effect(
        fixture_id=fixture_id,
        effect=effect,
        duration=duration,
        data=params if isinstance(params, dict) else {},
        request_id=None,
    )
    if not result.get("ok"):
        await manager.broadcast_event("warning", "preview_rejected", result)
        return False

    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    await manager.artnet_service.set_continuous_send(True)
    await manager.broadcast_event("info", "preview_started", result)
    return True
