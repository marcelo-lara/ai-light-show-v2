from __future__ import annotations

from typing import Any, Dict


async def execute_all_analyzer_items(manager, payload: Dict[str, Any]) -> bool:
    del payload
    try:
        result = await manager.analyzer_service.execute_all_queued()
    except Exception as exc:
        await manager.broadcast_event(
            "error",
            "analyzer_execute_failed",
            {"reason": "request_failed", "error": str(exc)},
        )
        return False
    await manager.broadcast_event("info", "analyzer_items_executed", result)
    return bool(result.get("count", 0))