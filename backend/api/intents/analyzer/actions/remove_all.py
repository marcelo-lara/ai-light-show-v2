from __future__ import annotations

from typing import Any, Dict


async def remove_all_analyzer_items(manager, payload: Dict[str, Any]) -> bool:
    del payload
    try:
        result = await manager.analyzer_service.remove_all_items()
    except Exception as exc:
        await manager.broadcast_event(
            "error",
            "analyzer_remove_failed",
            {"reason": "request_failed", "error": str(exc)},
        )
        return False
    await manager.broadcast_event("info", "analyzer_items_removed", result)
    return bool(result.get("count", 0))