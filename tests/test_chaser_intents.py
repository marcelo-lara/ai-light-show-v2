import pytest

from backend.api.intents.chaser.actions.apply import apply_chaser
from backend.api.intents.chaser.actions.list import list_chasers
from backend.api.intents.chaser.actions.preview import preview_chaser
from backend.api.intents.chaser.actions.start import start_chaser
from backend.api.intents.chaser.actions.stop import stop_chaser
from backend.api.intents.chaser.actions.stop_preview import stop_preview_chaser
from backend.api.intents.chaser.handlers import CHASER_HANDLERS


class _FakeStateManager:
    def __init__(self):
        self.preview_active = False
        self.preview_chaser_request_id = None
        self.output_universe = bytearray(512)
        self.lock = _NoopLock()

    def get_chasers(self):
        return [{"id": "downbeats_and_beats", "name": "Downbeat plus two beats", "description": "x", "effects": []}]

    async def get_output_universe(self):
        return bytearray(self.output_universe)

    async def apply_chaser(self, chaser_id, start_time_ms, repetitions):
        if chaser_id == "bad":
            return {"ok": False, "reason": "unknown_chaser"}
        return {
            "ok": True,
            "chaser_id": chaser_id,
            "entry": {"time": start_time_ms / 1000, "chaser_id": chaser_id, "data": {"repetitions": repetitions}},
        }

    async def start_chaser_instance(self, chaser_id, start_time_ms, repetitions):
        if chaser_id == "bad":
            return {"ok": False, "reason": "unknown_chaser"}
        return {"ok": True, "instance_id": "chaser-1", "chaser_id": chaser_id}

    async def stop_chaser_instance(self, instance_id):
        if instance_id != "chaser-1":
            return {"ok": False, "reason": "unknown_instance_id"}
        return {"ok": True, "instance_id": instance_id}

    async def start_preview_chaser(self, chaser_id, start_time_ms, repetitions, request_id=None):
        del start_time_ms, repetitions, request_id
        if chaser_id == "bad":
            return {"ok": False, "reason": "unknown_chaser"}
        self.preview_active = True
        self.preview_chaser_request_id = "preview-1"
        return {"ok": True, "requestId": "preview-1", "chaser_id": chaser_id, "entries": 4}

    async def cancel_preview_chaser(self):
        if not self.preview_active:
            return False
        self.preview_active = False
        self.preview_chaser_request_id = None
        return True


class _NoopLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


class _FakeArtNetService:
    def __init__(self):
        self.frames = []
        self.continuous_send = False

    async def update_universe(self, universe):
        self.frames.append(bytearray(universe))

    async def set_continuous_send(self, enabled: bool):
        self.continuous_send = bool(enabled)


class _FakeManager:
    def __init__(self):
        self.state_manager = _FakeStateManager()
        self.artnet_service = _FakeArtNetService()
        self.events = []

    async def broadcast_event(self, level, message, data):
        self.events.append((level, message, data))


@pytest.mark.asyncio
async def test_apply_chaser_intent_success():
    manager = _FakeManager()
    ok = await apply_chaser(manager, {"chaser_id": "downbeats_and_beats", "start_time_ms": 0, "repetitions": 1})
    assert ok is True
    assert manager.events[-1][1] == "chaser_applied"


@pytest.mark.asyncio
async def test_apply_chaser_intent_success_without_repetitions():
    manager = _FakeManager()
    ok = await apply_chaser(manager, {"chaser_id": "downbeats_and_beats", "start_time_ms": 0})
    assert ok is True
    assert manager.events[-1][1] == "chaser_applied"


@pytest.mark.asyncio
async def test_start_chaser_intent_success():
    manager = _FakeManager()
    ok = await start_chaser(manager, {"chaser_id": "downbeats_and_beats"})
    assert ok is True
    assert manager.events[-1][1] == "chaser_started"


@pytest.mark.asyncio
async def test_start_chaser_intent_success_without_repetitions():
    manager = _FakeManager()
    ok = await start_chaser(manager, {"chaser_id": "downbeats_and_beats"})
    assert ok is True
    assert manager.events[-1][1] == "chaser_started"


@pytest.mark.asyncio
async def test_stop_chaser_intent_returns_no_patch():
    manager = _FakeManager()
    ok = await stop_chaser(manager, {"instance_id": "chaser-1"})
    assert ok is False
    assert manager.events[-1][1] == "chaser_stopped"


@pytest.mark.asyncio
async def test_list_chasers_intent_emits_event_only():
    manager = _FakeManager()
    ok = await list_chasers(manager, {})
    assert ok is False
    assert manager.events[-1][1] == "chaser_list"
    assert isinstance(manager.events[-1][2]["chasers"], list)


@pytest.mark.asyncio
async def test_preview_chaser_intent_success():
    manager = _FakeManager()
    ok = await preview_chaser(manager, {"chaser_id": "downbeats_and_beats"})
    assert ok is True
    assert manager.events[-1][1] == "chaser_preview_started"
    await stop_preview_chaser(manager, {})


@pytest.mark.asyncio
async def test_preview_chaser_stop_event_only():
    manager = _FakeManager()
    await preview_chaser(manager, {"chaser_id": "downbeats_and_beats"})
    ok = await stop_preview_chaser(manager, {})
    assert ok is False
    assert manager.events[-1][1] == "chaser_preview_stopped"


def test_chaser_handlers_map_contains_full_names():
    assert "chaser.apply" in CHASER_HANDLERS
    assert "chaser.preview" in CHASER_HANDLERS
    assert "chaser.stop_preview" in CHASER_HANDLERS
    assert "chaser.start" in CHASER_HANDLERS
    assert "chaser.stop" in CHASER_HANDLERS
    assert "chaser.list" in CHASER_HANDLERS
