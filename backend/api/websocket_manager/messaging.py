from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import logging

from fastapi import WebSocket

from api.intents.apply_intent import apply_intent
from api.state.build_frontend_state import build_frontend_state

logger = logging.getLogger(__name__)


async def send_snapshot(manager, websocket: WebSocket) -> None:
    state = await build_frontend_state(manager)
    manager._last_state_snapshot = state
    msg = {"type": "snapshot", "seq": manager._next_seq(), "state": state}
    logger.info("[WS] Sending snapshot to client (seq=%s) with %s fixtures", msg["seq"], len(state.get("fixtures", {})))
    for fid, fstate in state.get("fixtures", {}).items():
        logger.debug("[WS] Fixture %s: values=%s", fid, fstate.get("values"))
    await websocket.send_json(msg)


async def broadcast(manager, message: dict) -> None:
    stale: List[WebSocket] = []
    for connection in manager.active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            stale.append(connection)
    for connection in stale:
        manager.disconnect(connection)


async def broadcast_event(manager, level: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {"type": "event", "level": level, "message": message}
    if data is not None:
        payload["data"] = data
    await manager.broadcast(payload)


async def handle_message(manager, websocket: WebSocket, data: str) -> None:
    try:
        message = json.loads(data)
    except Exception:
        await websocket.send_json({"type": "event", "level": "error", "message": "invalid_json"})
        return

    msg_type = message.get("type")
    if msg_type == "hello":
        await manager.send_snapshot(websocket)
        return
    if msg_type != "intent":
        await websocket.send_json(
            {"type": "event", "level": "warning", "message": "unsupported_message_type", "data": {"type": msg_type}}
        )
        return

    name = str(message.get("name") or "")
    payload = message.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    if not manager._last_state_snapshot:
        manager._last_state_snapshot = await build_frontend_state(manager)

    changed = await apply_intent(manager, name, payload)
    if changed:
        await manager._schedule_broadcast()
