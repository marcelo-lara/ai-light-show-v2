from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import json
import asyncio
import time
import logging

from fastapi import WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from backend.store.state import StateManager
    from backend.services.artnet import ArtNetService
    from backend.services.song_service import SongService

from backend.api.ws_handlers import apply_intent
from backend.api.ws_state_builder import build_frontend_state

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self, state_manager: StateManager, artnet_service: ArtNetService, song_service: SongService):
        self.state_manager = state_manager
        self.artnet_service = artnet_service
        self.song_service = song_service
        self.active_connections: List[WebSocket] = []
        self.seq: int = 0
        self.fixture_armed: Dict[str, bool] = {}
        
        # Throttling state
        self._last_broadcast_time = 0.0
        self._broadcast_throttle_ms = 50  # ~20 FPS for state updates
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
        state = await build_frontend_state(self)
        self._last_state_snapshot = state # track last state for future patching
        msg = {
            "type": "snapshot",
            "seq": self._next_seq(),
            "state": state,
        }
        logger.info(f"[WS] Sending snapshot to client (seq={msg['seq']}) with {len(state.get('fixtures', {}))} fixtures")
        # Log fixtures state specifically as requested
        for fid, fstate in state.get("fixtures", {}).items():
            logger.debug(f"[WS] Fixture {fid}: values={fstate.get('values')}")
        await websocket.send_json(msg)

    async def broadcast(self, message: dict):
        stale: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)

    async def broadcast_event(self, level: str, message: str, data: Optional[Dict[str, Any]] = None):
        payload: Dict[str, Any] = {
            "type": "event",
            "level": level,
            "message": message,
        }
        if data is not None:
            payload["data"] = data
        await self.broadcast(payload)

    async def handle_message(self, websocket: WebSocket, data: str):
        try:
            message = json.loads(data)
        except Exception:
            await websocket.send_json({
                "type": "event",
                "level": "error",
                "message": "invalid_json",
            })
            return

        msg_type = message.get("type")

        if msg_type == "hello":
            await self.send_snapshot(websocket)
            return

        if msg_type != "intent":
            await websocket.send_json({
                "type": "event",
                "level": "warning",
                "message": "unsupported_message_type",
                "data": {"type": msg_type},
            })
            return

        name = str(message.get("name") or "")
        payload = message.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}

        if not self._last_state_snapshot:
            self._last_state_snapshot = await build_frontend_state(self)

        changed = await apply_intent(self, name, payload)

        if changed:
            await self._schedule_broadcast()

    async def _schedule_broadcast(self):
        """Schedules a throttled broadcast of the current state."""
        now = time.time()
        time_since_last = (now - self._last_broadcast_time) * 1000.0

        if self._pending_broadcast_task and not self._pending_broadcast_task.done():
            # Already a broadcast pending, it will pick up the latest state
            return

        if time_since_last >= self._broadcast_throttle_ms:
            # Enough time has passed, broadcast immediately
            await self._execute_broadcast()
        else:
            # Schedule for later
            delay = (self._broadcast_throttle_ms - time_since_last) / 1000.0
            self._pending_broadcast_task = asyncio.create_task(self._delayed_broadcast(delay))

    async def _delayed_broadcast(self, delay: float):
        await asyncio.sleep(delay)
        await self._execute_broadcast()

    async def _execute_broadcast(self):
        if not self.active_connections:
            return

        new_state = await build_frontend_state(self)
        if self._last_state_snapshot:
            await self._broadcast_patch(self._last_state_snapshot, new_state)
        else:
            # Fallback if no last snapshot exists (should be rare after first snapshot)
            logger.warning("[WS] No previous snapshot to patch against, sending full snapshot")
            await self.broadcast({
                "type": "snapshot",
                "seq": self._next_seq(),
                "state": new_state,
            })
            
        self._last_state_snapshot = new_state
        self._last_broadcast_time = time.time()

    async def _broadcast_patch(self, before: Dict[str, Any], after: Dict[str, Any]):
        changes = []
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            if before.get(key) != after.get(key):
                changes.append({"path": [key], "value": after.get(key)})

        if not changes:
            return

        seq = self._next_seq()
        logger.info(f"[WS] Broadcasting patch (seq={seq}) with {len(changes)} changes")
        for change in changes:
            if change["path"] == ["fixtures"]:
                logger.debug(f"[WS] Fixtures changed: {json.dumps(change['value'], indent=2)}")

        await self.broadcast({
            "type": "patch",
            "seq": seq,
            "changes": changes,
        })

    def _ensure_arm_state_initialized(self):
        if self.fixture_armed:
            return
        for fixture in self.state_manager.fixtures:
            self.fixture_armed[fixture.id] = True

    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq

async def websocket_endpoint(websocket: WebSocket, manager: WebSocketManager):
    logger.info(f"[WS] Connect request from {websocket.client}")
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"[WS] Message received: {data[:100]}...")
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        logger.info("[WS] Disconnected")
        manager.disconnect(websocket)
