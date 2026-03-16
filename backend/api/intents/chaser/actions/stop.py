from __future__ import annotations

from typing import Any, Dict


async def stop_chaser(manager, payload: Dict[str, Any]) -> bool:
    instance_id = str(payload.get("instance_id") or "").strip()
    if not instance_id:
        await manager.broadcast_event("error", "chaser_stop_failed", {"reason": "missing_instance_id"})
        return False

    result = await manager.state_manager.stop_chaser_instance(instance_id)
    if not result.get("ok"):
        await manager.broadcast_event("error", "chaser_stop_failed", result)
        return False

    await manager.broadcast_event("info", "chaser_stopped", result)
    return False
