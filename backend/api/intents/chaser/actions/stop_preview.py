from __future__ import annotations

from typing import Any, Dict


async def stop_preview_chaser(manager, payload: Dict[str, Any]) -> bool:
    del payload
    stopped = await manager.state_manager.cancel_preview_chaser()
    if not stopped:
        await manager.broadcast_event("warning", "chaser_preview_stop_ignored", {"reason": "preview_not_active"})
        return False
    await manager.broadcast_event("info", "chaser_preview_stopped", {})
    return False