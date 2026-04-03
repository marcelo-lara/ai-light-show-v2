from __future__ import annotations

from typing import Any, Dict

from .helpers import resolve_song_params


async def enqueue_full_artifact_playlist(manager, payload: Dict[str, Any]) -> bool:
    params, params_error = resolve_song_params(manager, payload)
    if params_error is not None:
        await manager.broadcast_event("error", "analyzer_enqueue_failed", params_error)
        return False
    activate = payload.get("activate")
    activate_flag = True if activate is None else bool(activate)
    try:
        result = await manager.analyzer_service.enqueue_full_artifact_playlist(params, activate=activate_flag)
    except Exception as exc:
        await manager.broadcast_event(
            "error",
            "analyzer_enqueue_failed",
            {"reason": "request_failed", "playlist": "full-artifact", "filename": params["filename"], "error": str(exc)},
        )
        return False
    await manager.broadcast_event(
        "info",
        "analyzer_playlist_enqueued",
        {
            "playlist": "full-artifact",
            "filename": params["filename"],
            "activate": activate_flag,
            "resolved_playlist": result.get("playlist"),
            **{key: value for key, value in result.items() if key != "playlist"},
        },
    )
    return True