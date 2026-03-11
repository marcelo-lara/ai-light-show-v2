from __future__ import annotations

from typing import Any, Dict


async def stop(manager, payload: Dict[str, Any]) -> bool:
    await manager.state_manager.set_playback_state(False)
    await manager.state_manager.seek_timecode(0.0)
    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    await manager.artnet_service.set_continuous_send(False)
    return True
