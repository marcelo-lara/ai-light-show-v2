from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from ..playlists.full_artifact import build_full_artifact_playlist, execute_full_artifact_playlist, get_playlist, list_playlists
from ..task_queue import add_item, add_playlist_items, execute_item, get_item, get_task_types, list_items, remove_item
from ..tasks.catalog import get_task_type
from .models import FullArtifactPlaylistRequest, PlaybackLockUpdate, QueueFullArtifactPlaylistRequest, QueueItemCreate


def register_routes(app: FastAPI) -> None:
    @app.get("/")
    async def root() -> dict[str, Any]:
        return {"message": "AI Light Show v2 Analyzer"}

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True}

    @app.get("/task-types")
    async def task_types() -> dict[str, Any]:
        return {"ok": True, "task_types": get_task_types()}

    @app.get("/task-types/{task_type}")
    async def task_type(task_type: str) -> dict[str, Any]:
        payload = get_task_type(task_type)
        if payload is None:
            raise HTTPException(status_code=404, detail="task_type_not_found")
        return {"ok": True, "task_type": payload}

    @app.get("/queue/status")
    async def queue_status() -> dict[str, Any]:
        return _status_payload(app)

    @app.get("/queue/items")
    async def queue_items() -> dict[str, Any]:
        return {"ok": True, "items": list_items(app.state.queue_path)}

    @app.get("/queue/items/{item_id}")
    async def queue_item(item_id: str) -> dict[str, Any]:
        item = get_item(item_id, app.state.queue_path)
        if item is None:
            raise HTTPException(status_code=404, detail="queue_item_not_found")
        return {"ok": True, "item": item}

    @app.post("/queue/items")
    async def queue_add(payload: QueueItemCreate) -> dict[str, Any]:
        return {"ok": True, "item_id": add_item(payload.task_type, payload.params, app.state.queue_path)}

    @app.delete("/queue/items/{item_id}")
    async def queue_delete(item_id: str) -> dict[str, Any]:
        if not remove_item(item_id, app.state.queue_path):
            raise HTTPException(status_code=404, detail="queue_item_not_found")
        return {"ok": True, "item_id": item_id}

    @app.post("/queue/items/{item_id}/execute")
    async def queue_execute(item_id: str) -> dict[str, Any]:
        item = execute_item(item_id, app.state.queue_path)
        if item is None:
            raise HTTPException(status_code=409, detail="queue_item_not_executable")
        return {"ok": True, "item": item}

    @app.post("/queue/playlists/full-artifact")
    async def queue_full_artifact_playlist(payload: QueueFullArtifactPlaylistRequest) -> dict[str, Any]:
        playlist = build_full_artifact_playlist(payload.song_path, payload.meta_path, device=payload.device)
        scheduled = add_playlist_items(playlist["tasks"], app.state.queue_path, activate=payload.activate)
        return {"ok": True, "playlist": playlist, "scheduled": scheduled}

    @app.post("/runtime/playback-lock")
    async def playback_lock(payload: PlaybackLockUpdate) -> dict[str, Any]:
        app.state.playback_locked = bool(payload.locked)
        return _status_payload(app)

    @app.get("/playlists/full-artifact")
    async def full_artifact_playlist(song_path: str = Query(...), meta_path: str = Query("/app/meta"), device: str | None = Query(None)) -> dict[str, Any]:
        return {"ok": True, "playlist": build_full_artifact_playlist(song_path, meta_path, device=device)}

    @app.get("/playlists")
    async def playlists() -> dict[str, Any]:
        return {"ok": True, "playlists": list_playlists()}

    @app.get("/playlists/full-artifact/metadata")
    async def full_artifact_playlist_metadata() -> dict[str, Any]:
        payload = get_playlist("full-artifact")
        if payload is None:
            raise HTTPException(status_code=404, detail="playlist_not_found")
        return {"ok": True, "playlist": payload}

    @app.post("/playlists/full-artifact/execute")
    async def execute_playlist(payload: FullArtifactPlaylistRequest) -> dict[str, Any]:
        return {
            "ok": True,
            "result": execute_full_artifact_playlist(payload.song_path, payload.meta_path, device=payload.device),
        }


def _status_payload(app: FastAPI) -> dict[str, Any]:
    items = list_items(app.state.queue_path)
    summary = {status: sum(1 for item in items if item.get("status") == status) for status in ["queued", "pending", "running", "complete", "failed"]}
    return {
        "ok": True,
        "playback_locked": app.state.playback_locked,
        "polling": bool(app.state.worker_task and not app.state.worker_task.done()),
        "items": items,
        "summary": summary,
    }