from __future__ import annotations

from typing import Any, Dict, Optional
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from api.intents.apply_intent import apply_intent
from api.state.build_frontend_state import build_frontend_state

logger = logging.getLogger(__name__)


def _is_disconnect_error(exc: Exception) -> bool:
    if isinstance(exc, WebSocketDisconnect):
        return True
    if isinstance(exc, RuntimeError) and "WebSocket is not connected" in str(exc):
        return True
    return False


async def _safe_send_json(manager, websocket: WebSocket, payload: Dict[str, Any]) -> bool:
    try:
        await websocket.send_json(payload)
        return True
    except Exception as exc:
        if _is_disconnect_error(exc):
            logger.info("[WS] Dropping disconnected client during send")
        else:
            logger.warning("[WS] Send failed; dropping client: %s", exc)
        manager.disconnect(websocket)
        return False


async def send_snapshot(manager, websocket: WebSocket) -> None:
    state = await build_frontend_state(manager)
    manager._last_state_snapshot = state
    msg = {"type": "snapshot", "seq": manager._next_seq(), "state": state}
    logger.info("[WS] Sending snapshot to client (seq=%s) with %s fixtures", msg["seq"], len(state.get("fixtures", {})))
    for fid, fstate in state.get("fixtures", {}).items():
        logger.debug("[WS] Fixture %s: values=%s", fid, fstate.get("values"))
    await _safe_send_json(manager, websocket, msg)


async def broadcast(manager, message: dict) -> None:
    for connection in list(manager.active_connections):
        await _safe_send_json(manager, connection, message)


async def broadcast_event(manager, level: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {"type": "event", "level": level, "message": message}
    if data is not None:
        payload["data"] = data
    await manager.broadcast(payload)


async def send_event(manager, websocket: WebSocket, level: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {"type": "event", "level": level, "message": message}
    if data is not None:
        payload["data"] = data
    await _safe_send_json(manager, websocket, payload)


async def send_event_to_client(manager, client_id: str, level: str, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
    websocket = manager.client_connections.get(client_id)
    if websocket is None:
        return False
    payload: Dict[str, Any] = {"type": "event", "level": level, "message": message}
    if data is not None:
        payload["data"] = data
    return await _safe_send_json(manager, websocket, payload)


async def handle_message(manager, websocket: WebSocket, data: str) -> None:
    try:
        message = json.loads(data)
    except Exception:
        await _safe_send_json(manager, websocket, {"type": "event", "level": "error", "message": "invalid_json"})
        return

    msg_type = message.get("type")
    if msg_type == "hello":
        await manager.send_snapshot(websocket)
        return
    if msg_type != "intent":
        await _safe_send_json(
            manager,
            websocket,
            {"type": "event", "level": "warning", "message": "unsupported_message_type", "data": {"type": msg_type}}
        )
        return

    name = str(message.get("name") or "")
    payload = message.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    payload = {**payload, "_req_id": str(message.get("req_id") or ""), "_client_id": str(id(websocket))}

    if name == "transport.jump_to_time":
        logger.debug("[WS] Intent received: %s", name)
    else:
        logger.info("[WS] Intent received: %s", name)

    if not manager._last_state_snapshot:
        manager._last_state_snapshot = await build_frontend_state(manager)

    changed = await apply_intent(manager, name, payload)
    if changed:
        await manager._schedule_broadcast()
