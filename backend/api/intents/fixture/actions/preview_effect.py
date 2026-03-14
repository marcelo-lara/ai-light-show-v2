from __future__ import annotations

import asyncio
from typing import Any, Dict

FPS = 60


async def _preview_sync_loop(manager, request_id: str) -> None:
    """Sync state_manager.output_universe to artnet_service while preview runs."""
    try:
        while True:
            sm = manager.state_manager
            async with sm.lock:
                if not sm.preview_active or sm.preview_request_id != request_id:
                    # Preview ended - sync one final time to push restored values
                    universe = bytearray(sm.output_universe)
                    break
                universe = bytearray(sm.output_universe)
            await manager.artnet_service.update_universe(universe)
            await asyncio.sleep(1.0 / FPS)
        # Push restored values to ArtNet
        await manager.artnet_service.update_universe(universe)
    except asyncio.CancelledError:
        pass
    finally:
        await manager.artnet_service.set_continuous_send(False)


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

    request_id = result.get("requestId", "")
    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    await manager.artnet_service.set_continuous_send(True)

    # Start background sync loop to push frames to ArtNet during preview
    asyncio.create_task(_preview_sync_loop(manager, request_id))

    await manager.broadcast_event("info", "preview_started", result)
    return True
