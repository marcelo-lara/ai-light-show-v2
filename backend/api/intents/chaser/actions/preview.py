from __future__ import annotations

import asyncio
from typing import Any, Dict

FPS = 60


async def _preview_sync_loop(manager, request_id: str) -> None:
    try:
        while True:
            sm = manager.state_manager
            async with sm.lock:
                if not sm.preview_chaser_active or sm.preview_chaser_request_id != request_id:
                    universe = bytearray(sm.output_universe)
                    break
                universe = bytearray(sm.output_universe)
            await manager.artnet_service.update_universe(universe)
            await asyncio.sleep(1.0 / FPS)
        await manager.artnet_service.update_universe(universe)
    except asyncio.CancelledError:
        pass
    finally:
        await manager.artnet_service.set_continuous_send(False)


async def preview_chaser(manager, payload: Dict[str, Any]) -> bool:
    chaser_name = str(payload.get("chaser_name") or "").strip()
    if not chaser_name:
        await manager.broadcast_event("error", "chaser_preview_failed", {"reason": "missing_chaser_name"})
        return False

    start_time_ms = payload.get("start_time_ms", 0)
    repetitions = payload.get("repetitions")
    try:
        start_time_ms_f = max(0.0, float(start_time_ms))
        repetitions_i = 1 if repetitions is None else max(1, int(repetitions))
    except (TypeError, ValueError):
        await manager.broadcast_event("error", "chaser_preview_failed", {"reason": "invalid_payload"})
        return False

    result = await manager.state_manager.start_preview_chaser(
        chaser_name=chaser_name,
        start_time_ms=start_time_ms_f,
        repetitions=repetitions_i,
        request_id=None,
    )
    if not result.get("ok"):
        await manager.broadcast_event("warning", "chaser_preview_rejected", result)
        return False

    request_id = str(result.get("requestId") or "")
    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    await manager.artnet_service.set_continuous_send(True)
    asyncio.create_task(_preview_sync_loop(manager, request_id))
    await manager.broadcast_event("info", "chaser_preview_started", result)
    return True