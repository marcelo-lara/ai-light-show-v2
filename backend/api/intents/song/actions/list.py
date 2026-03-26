from __future__ import annotations

from typing import Any, Dict


async def list_songs(manager, payload: Dict[str, Any]) -> bool:
    del payload
    await manager.broadcast_event("info", "song_list", {"songs": manager.song_service.list_songs()})
    return False