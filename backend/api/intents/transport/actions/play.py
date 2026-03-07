from __future__ import annotations

from typing import Any, Dict


async def play(manager, payload: Dict[str, Any]) -> bool:
    await manager.state_manager.set_playback_state(True)
    await manager.artnet_service.set_continuous_send(True)
    return True
