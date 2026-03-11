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
