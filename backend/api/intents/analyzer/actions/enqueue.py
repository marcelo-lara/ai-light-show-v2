from __future__ import annotations

from typing import Any, Dict

from api.intents.analyzer.actions.helpers import resolve_song_params, validate_task_type


async def enqueue_analyzer_item(manager, payload: Dict[str, Any]) -> bool:
    task_type, task_error = validate_task_type(payload)
    if task_error is not None:
        await manager.broadcast_event("error", "analyzer_enqueue_failed", task_error)
        return False

    params, params_error = resolve_song_params(manager, payload)
    if params_error is not None:
        await manager.broadcast_event("error", "analyzer_enqueue_failed", params_error)
        return False

    try:
        result = await manager.analyzer_service.enqueue_item(task_type, params)
    except Exception as exc:
        await manager.broadcast_event(
            "error",
            "analyzer_enqueue_failed",
            {"reason": "request_failed", "task_type": task_type, "filename": params["filename"], "error": str(exc)},
        )
        return False
    await manager.broadcast_event(
        "info",
        "analyzer_item_enqueued",
        {"task_type": task_type, "filename": params["filename"], **result},
    )
    return True