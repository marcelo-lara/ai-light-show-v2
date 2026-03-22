from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import asyncio
import time

from fastapi import WebSocket

from api.websocket_manager.broadcasting import broadcast_patch, execute_broadcast, schedule_broadcast
from api.websocket_manager.lifecycle import ensure_arm_state_initialized, next_seq
from api.websocket_manager.messaging import broadcast, broadcast_event, handle_message, send_snapshot

if TYPE_CHECKING:
    from backend.store.state import StateManager
    from backend.services.artnet import ArtNetService
    from backend.services.song_service import SongService


class WebSocketManager:
    def __init__(self, state_manager: StateManager, artnet_service: ArtNetService, song_service: SongService):
        self.state_manager = state_manager
        self.artnet_service = artnet_service
        self.song_service = song_service
        self.active_connections: List[WebSocket] = []
        self.seq: int = 0
        self.fixture_armed: Dict[str, bool] = {}
        self._last_broadcast_time = 0.0
        self._broadcast_throttle_ms = 50
        self._pending_broadcast_task: Optional[asyncio.Task] = None
        self._last_state_snapshot: Optional[Dict[str, Any]] = None
        self._playback_task: Optional[asyncio.Task] = None
        self._playback_task_running: bool = False
        self._llm_task: Optional[asyncio.Task] = None
        self._llm_request_id: Optional[str] = None

    async def start_playback_ticker(self) -> None:
        if self._playback_task and not self._playback_task.done():
            return
        self._playback_task_running = True
        self._playback_task = asyncio.create_task(self._playback_ticker_loop())

    async def stop_playback_ticker(self) -> None:
        self._playback_task_running = False
        if not self._playback_task:
            return
        self._playback_task.cancel()
        try:
            await self._playback_task
        except asyncio.CancelledError:
            pass
        self._playback_task = None

    def track_llm_task(self, task: asyncio.Task, request_id: str) -> None:
        self._llm_task = task
        self._llm_request_id = request_id
        task.add_done_callback(lambda done_task, active_id=request_id: self._clear_llm_task(active_id, done_task))

    async def cancel_llm_task(self) -> bool:
        task = self._llm_task
        self._llm_task = None
        self._llm_request_id = None
        if not task or task.done():
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    def _clear_llm_task(self, request_id: str, task: asyncio.Task) -> None:
        if self._llm_request_id != request_id:
            return
        self._llm_task = None
        self._llm_request_id = None

    async def _playback_ticker_loop(self) -> None:
        target_fps = 60.0
        frame_interval = 1.0 / target_fps
        last_tick = time.perf_counter()

        while self._playback_task_running:
            now = time.perf_counter()
            delta = now - last_tick
            if delta < frame_interval:
                await asyncio.sleep(frame_interval - delta)
                continue
            last_tick = now

            if not await self.state_manager.get_is_playing():
                continue

            await self.state_manager.advance_timecode(delta)
            universe = await self.state_manager.get_output_universe()
            await self.artnet_service.update_universe(universe)
            await self._schedule_broadcast()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self._ensure_arm_state_initialized()
        await self.send_snapshot(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_snapshot(self, websocket: WebSocket):
        await send_snapshot(self, websocket)

    async def broadcast(self, message: dict):
        await broadcast(self, message)

    async def broadcast_event(self, level: str, message: str, data: Optional[Dict[str, Any]] = None):
        await broadcast_event(self, level, message, data)

    async def handle_message(self, websocket: WebSocket, data: str):
        await handle_message(self, websocket, data)

    async def _schedule_broadcast(self):
        await schedule_broadcast(self, time.time())

    async def _execute_broadcast(self):
        await execute_broadcast(self, time.time())

    async def _broadcast_patch(self, before: Dict[str, Any], after: Dict[str, Any]):
        await broadcast_patch(self, before, after)

    def _ensure_arm_state_initialized(self):
        ensure_arm_state_initialized(self)

    def _next_seq(self) -> int:
        return next_seq(self)
