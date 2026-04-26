from __future__ import annotations

from typing import Any, Dict


async def create_human_hint(manager, payload: Dict[str, Any]) -> bool:
    result = await manager.state_manager.create_human_hint(payload)
    if not result.get("ok"):
        await manager.broadcast_event("error", "song_hint_create_failed", result)
        return False
    await manager.broadcast_event("info", "song_hint_created", result)
    return True