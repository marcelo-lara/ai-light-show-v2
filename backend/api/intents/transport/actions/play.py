from __future__ import annotations

from typing import Any, Dict


async def play(manager, payload: Dict[str, Any]) -> bool:
    analyzer_service = getattr(manager, "analyzer_service", None)
    if analyzer_service is not None:
        ok, status = await analyzer_service.lock_for_playback()
        if not ok:
            await manager.broadcast_event("warning", "transport_play_blocked", {"reason": "analyzer_running", "analyzer": status})
            return False
    await manager.state_manager.set_playback_state(True)
    await manager.start_playback_ticker()
    await manager.artnet_service.set_continuous_send(True)
    await manager.broadcast_event(
        "info",
        "transport_trace",
        {"action": "play", "is_playing": await manager.state_manager.get_is_playing()},
    )
    return True
