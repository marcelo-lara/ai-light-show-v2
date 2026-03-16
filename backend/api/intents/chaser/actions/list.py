from __future__ import annotations

from typing import Any, Dict


async def list_chasers(manager, payload: Dict[str, Any]) -> bool:
    del payload
    await manager.broadcast_event("info", "chaser_list", {"chasers": manager.state_manager.get_chasers()})
    return False
