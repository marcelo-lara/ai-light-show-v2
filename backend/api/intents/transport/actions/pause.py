from __future__ import annotations

from typing import Any, Dict


async def pause(manager, payload: Dict[str, Any]) -> bool:
    await manager.state_manager.set_playback_state(False)
    await manager.artnet_service.set_continuous_send(False)
    return True
