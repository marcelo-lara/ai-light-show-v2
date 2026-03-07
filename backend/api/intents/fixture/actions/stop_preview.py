from __future__ import annotations

from typing import Any, Dict


async def stop_preview(manager, payload: Dict[str, Any]) -> bool:
    await manager.broadcast_event("warning", "stop_preview_not_implemented")
    return False
