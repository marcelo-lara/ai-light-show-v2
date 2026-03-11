import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


async def websocket_endpoint(websocket: WebSocket, manager) -> None:
    logger.info("[WS] Connect request from %s", websocket.client)
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("[WS] Message received: %s...", data[:100])
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        logger.info("[WS] Disconnected")
        manager.disconnect(websocket)
