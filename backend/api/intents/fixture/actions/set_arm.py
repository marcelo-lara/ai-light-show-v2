from __future__ import annotations

from typing import Any, Dict


async def set_arm(manager, payload: Dict[str, Any]) -> bool:
    fixture_id = str(payload.get("fixture_id") or "")
    if not fixture_id:
        await manager.broadcast_event("error", "fixture_id_required")
        return False
    manager.fixture_armed[fixture_id] = bool(payload.get("armed", False))
    return True
