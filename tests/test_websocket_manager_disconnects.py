import pytest

from backend.api.websocket_manager.endpoint import websocket_endpoint
from backend.api.websocket_manager.messaging import send_snapshot


class _DisconnectingWebSocket:
    def __init__(self):
        self.client = "test-client"
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        self.messages.append(payload)
        raise RuntimeError('WebSocket is not connected. Need to call "accept" first.')


class _ReceiveClosedWebSocket:
    def __init__(self):
        self.client = "test-client"

    async def accept(self):
        return None

    async def receive_text(self):
        raise RuntimeError('WebSocket is not connected. Need to call "accept" first.')


class _Manager:
    def __init__(self):
        self.active_connections = []
        self.client_connections = {}
        self.disconnect_calls = []
        self._last_state_snapshot = None
        self.seq = 0

    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_connections[str(id(websocket))] = websocket

    def disconnect(self, websocket):
        self.disconnect_calls.append(websocket)
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_connections.pop(str(id(websocket)), None)

    async def handle_message(self, websocket, data):
        raise AssertionError(f"unexpected message handling for {websocket}: {data}")

    async def send_snapshot(self, websocket):
        await send_snapshot(self, websocket)

    def _next_seq(self):
        self.seq += 1
        return self.seq


@pytest.mark.asyncio
async def test_send_snapshot_disconnects_stale_socket(monkeypatch):
    manager = _Manager()
    websocket = _DisconnectingWebSocket()

    async def _fake_build_frontend_state(_manager):
        return {"fixtures": {}}

    monkeypatch.setattr("backend.api.websocket_manager.messaging.build_frontend_state", _fake_build_frontend_state)
    manager.active_connections.append(websocket)
    manager.client_connections[str(id(websocket))] = websocket

    await send_snapshot(manager, websocket)

    assert manager.disconnect_calls == [websocket]
    assert websocket not in manager.active_connections


@pytest.mark.asyncio
async def test_websocket_endpoint_treats_not_connected_runtime_as_disconnect():
    manager = _Manager()
    websocket = _ReceiveClosedWebSocket()

    await websocket_endpoint(websocket, manager)

    assert manager.disconnect_calls == [websocket]
