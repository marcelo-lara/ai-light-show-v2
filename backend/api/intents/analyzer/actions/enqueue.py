from __future__ import annotations

from typing import Any, Dict

from api.intents.analyzer.actions.helpers import is_supported_task_type, resolve_song_params, task_type_from_payload


async def enqueue_analyzer_item(manager, payload: Dict[str, Any]) -> bool:
    task_type, task_error = task_type_from_payload(payload)
    if task_error is not None:
        await manager.broadcast_event("error", "analyzer_enqueue_failed", task_error)
        return False
    task_types = manager.analyzer_service.task_types()
    if not task_types:
        task_types = await manager.analyzer_service.refresh_task_types()
    if not is_supported_task_type(task_type, task_types):
        await manager.broadcast_event("error", "analyzer_enqueue_failed", {"reason": "unsupported_task_type", "task_type": task_type})
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