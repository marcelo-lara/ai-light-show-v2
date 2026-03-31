from __future__ import annotations

from typing import Any, Dict


async def stop(manager, payload: Dict[str, Any]) -> bool:
    await manager.state_manager.set_playback_state(False)
    await manager.stop_playback_ticker()
    await manager.state_manager.seek_timecode(0.0)
    await manager.state_manager.blackout_output()
    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    await manager.artnet_service.set_continuous_send(False)
    analyzer_service = getattr(manager, "analyzer_service", None)
    if analyzer_service is not None:
        await analyzer_service.unlock_after_playback()
    await manager.broadcast_event(
        "info",
        "transport_trace",
        {
            "action": "stop",
            "is_playing": await manager.state_manager.get_is_playing(),
            "blackout": True,
        },
    )
    return True
