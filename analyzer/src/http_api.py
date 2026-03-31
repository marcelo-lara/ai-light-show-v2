from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .task_queue_api import add_item, execute_item, get_item, list_items, process_queue, remove_item
from .task_queue_store import QUEUE_FILE_PATH, clear_items


class QueueItemCreate(BaseModel):
    task_type: str
    params: dict[str, Any]


class PlaybackLockUpdate(BaseModel):
    locked: bool


def _status_payload(queue_path: Path, playback_locked: bool, polling: bool) -> dict[str, Any]:
    items = list_items(queue_path)
    summary = {status: sum(1 for item in items if item.get("status") == status) for status in ["queued", "pending", "running", "complete", "failed"]}
    return {"ok": True, "playback_locked": playback_locked, "polling": polling, "items": items, "summary": summary}


def create_app(queue_path: Path | None = None, worker_enabled: bool = True, worker_interval: float = 0.5) -> FastAPI:
    queue_path = queue_path or Path(os.getenv("ANALYZER_QUEUE_PATH", str(QUEUE_FILE_PATH)))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.queue_path = queue_path
        app.state.playback_locked = False
        app.state.worker_task = None
        clear_items(app.state.queue_path)

        async def worker_loop() -> None:
            while True:
                if not app.state.playback_locked:
                    await asyncio.to_thread(process_queue, app.state.queue_path)
                await asyncio.sleep(worker_interval)

        if worker_enabled:
            app.state.worker_task = asyncio.create_task(worker_loop())
        try:
            yield
        finally:
            task = app.state.worker_task
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(title="AI Light Show v2 Analyzer", lifespan=lifespan)

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {"message": "AI Light Show v2 Analyzer"}

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True}

    @app.get("/queue/status")
    async def queue_status() -> dict[str, Any]:
        return _status_payload(app.state.queue_path, app.state.playback_locked, bool(app.state.worker_task and not app.state.worker_task.done()))

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

    @app.post("/runtime/playback-lock")
    async def playback_lock(payload: PlaybackLockUpdate) -> dict[str, Any]:
        app.state.playback_locked = bool(payload.locked)
        return _status_payload(app.state.queue_path, app.state.playback_locked, bool(app.state.worker_task and not app.state.worker_task.done()))

    return app


app = create_app()