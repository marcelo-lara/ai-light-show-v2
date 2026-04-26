from __future__ import annotations

from typing import Dict


async def delete_human_hint(manager, payload: Dict[str, object]) -> bool:
    hint_id = str(payload.get("id") or "").strip()
    if not hint_id:
        await manager.broadcast_event("error", "song_hint_delete_failed", {"reason": "missing_id"})
        return False
    result = await manager.state_manager.delete_human_hint(hint_id)
    if not result.get("ok"):
        await manager.broadcast_event("error", "song_hint_delete_failed", result)
        return False
    await manager.broadcast_event("info", "song_hint_deleted", result)
    return True