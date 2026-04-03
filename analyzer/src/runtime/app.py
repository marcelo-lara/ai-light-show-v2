from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from ..api import register_routes
from ..task_queue import QUEUE_FILE_PATH, clear_items, process_queue


def create_app(queue_path: Path | None = None, worker_enabled: bool = True, worker_interval: float = 0.5) -> FastAPI:
    resolved_queue_path = queue_path or Path(os.getenv("ANALYZER_QUEUE_PATH", str(QUEUE_FILE_PATH)))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.queue_path = resolved_queue_path
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
    register_routes(app)
    return app


app = create_app()