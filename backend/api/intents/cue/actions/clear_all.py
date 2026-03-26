from __future__ import annotations

from typing import Any, Dict


async def clear_all_cues(manager, payload: Dict[str, Any]) -> bool:
    del payload
    result = await manager.state_manager.clear_all_cue_entries()
    if not result.get("ok"):
        await manager.broadcast_event("error", "cue_clear_failed", result)
        return False

    await manager.broadcast_event("info", "cue_cleared", result)
    return True