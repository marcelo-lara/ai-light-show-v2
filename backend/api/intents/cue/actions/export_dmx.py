from __future__ import annotations


async def export_dmx(manager, payload) -> bool:
    del payload
    result = await manager.state_manager.rerender_dmx_canvas()
    if not result.get("ok"):
        await manager.broadcast_event("error", "cue_export_dmx_failed", result)
        return False

    await manager.broadcast_event("info", "cue_dmx_exported", result)
    return False