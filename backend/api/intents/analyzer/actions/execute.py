from __future__ import annotations

from typing import Any, Dict

from api.intents.analyzer.actions.helpers import item_id_from_payload


async def execute_analyzer_item(manager, payload: Dict[str, Any]) -> bool:
    item_id, item_error = item_id_from_payload(payload)
    if item_error is not None:
        await manager.broadcast_event("error", "analyzer_execute_failed", item_error)
        return False

    try:
        result = await manager.analyzer_service.execute_item(item_id)
    except Exception as exc:
        await manager.broadcast_event(
            "error",
            "analyzer_execute_failed",
            {"reason": "request_failed", "item_id": item_id, "error": str(exc)},
        )
        return False
    await manager.broadcast_event("info", "analyzer_item_executed", {"item_id": item_id, **result})
    return True