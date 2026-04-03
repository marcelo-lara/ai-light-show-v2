from __future__ import annotations


async def reload_cue_sheet(manager, payload) -> bool:
    del payload
    result = await manager.state_manager.reload_cue_sheet_from_disk()
    if not result.get("ok"):
        await manager.broadcast_event("error", "cue_reload_failed", result)
        return False

    await manager.broadcast_event("info", "cue_reloaded", result)
    return True