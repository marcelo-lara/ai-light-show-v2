from __future__ import annotations

from typing import Any, Dict


async def jump_to_time(manager, payload: Dict[str, Any]) -> bool:
    raw = payload.get("time_ms")
    sync_seek = bool(payload.get("sync"))
    try:
        target = max(0.0, float(str(raw)) / 1000.0)
    except Exception:
        await manager.broadcast_event("error", "invalid_time_ms")
        return False
    current_timecode = await manager.state_manager.get_timecode()
    if sync_seek and abs(current_timecode - target) < 0.01:
        return False
    await manager.state_manager.seek_timecode(target)
    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    return not sync_seek
