from __future__ import annotations

from typing import Any, Dict


async def pause(manager, payload: Dict[str, Any]) -> bool:
    await manager.state_manager.set_playback_state(False)
    await manager.stop_playback_ticker()
    await manager.artnet_service.set_continuous_send(False)
    await manager.broadcast_event(
        "info",
        "transport_trace",
        {"action": "pause", "is_playing": await manager.state_manager.get_is_playing()},
    )
    return True
