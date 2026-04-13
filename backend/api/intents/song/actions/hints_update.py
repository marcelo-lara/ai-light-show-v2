from __future__ import annotations

from typing import Any, Dict


ALLOWED_PATCH_FIELDS = {"start_time", "end_time", "title", "summary", "lighting_hint"}


async def update_human_hint(manager, payload: Dict[str, Any]) -> bool:
    hint_id = str(payload.get("id") or "").strip()
    patch = payload.get("patch") or {}
    if not hint_id:
        await manager.broadcast_event("error", "song_hint_update_failed", {"reason": "missing_id"})
        return False
    if not isinstance(patch, dict):
        await manager.broadcast_event("error", "song_hint_update_failed", {"reason": "missing_patch", "id": hint_id})
        return False
    filtered_patch = {key: value for key, value in patch.items() if key in ALLOWED_PATCH_FIELDS}
    if not filtered_patch:
        await manager.broadcast_event("error", "song_hint_update_failed", {"reason": "missing_patch", "id": hint_id})
        return False
    result = await manager.state_manager.update_human_hint(hint_id, filtered_patch)
    if not result.get("ok"):
        await manager.broadcast_event("error", "song_hint_update_failed", result)
        return False
    await manager.broadcast_event("info", "song_hint_updated", result)
    return True