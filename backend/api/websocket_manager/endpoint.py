import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


async def websocket_endpoint(websocket: WebSocket, manager) -> None:
    logger.info("[WS] Connect request from %s", websocket.client)
    try:
        await manager.connect(websocket)
        while True:
            data = await websocket.receive_text()
            logger.debug("[WS] Message received: %s...", data[:100])
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        logger.info("[WS] Disconnected")
    except RuntimeError as exc:
        if "WebSocket is not connected" not in str(exc):
            raise
        logger.info("[WS] Disconnected")
    finally:
        manager.disconnect(websocket)
