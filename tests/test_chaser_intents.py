import pytest

from backend.api.intents.chaser.actions.apply import apply_chaser
from backend.api.intents.chaser.actions.list import list_chasers
from backend.api.intents.chaser.actions.start import start_chaser
from backend.api.intents.chaser.actions.stop import stop_chaser
from backend.api.intents.chaser.handlers import CHASER_HANDLERS


class _FakeStateManager:
    def get_chasers(self):
        return [{"name": "Downbeat plus two beats", "description": "x", "effects": []}]

    async def apply_chaser(self, chaser_name, start_time_ms, repetitions):
        if chaser_name == "bad":
            return {"ok": False, "reason": "unknown_chaser"}
        return {
            "ok": True,
            "chaser_name": chaser_name,
            "entries": 4,
            "generated": 4,
            "replaced": 0,
            "skipped": 0,
        }

    async def start_chaser_instance(self, chaser_name, start_time_ms, repetitions):
        if chaser_name == "bad":
            return {"ok": False, "reason": "unknown_chaser"}
        return {"ok": True, "instance_id": "chaser-1", "chaser_name": chaser_name}

    async def stop_chaser_instance(self, instance_id):
        if instance_id != "chaser-1":
            return {"ok": False, "reason": "unknown_instance_id"}
        return {"ok": True, "instance_id": instance_id}


class _FakeManager:
    def __init__(self):
        self.state_manager = _FakeStateManager()
        self.events = []

    async def broadcast_event(self, level, message, data):
        self.events.append((level, message, data))


@pytest.mark.asyncio
async def test_apply_chaser_intent_success():
    manager = _FakeManager()
    ok = await apply_chaser(manager, {"chaser_name": "Downbeat plus two beats", "start_time_ms": 0, "repetitions": 1})
    assert ok is True
    assert manager.events[-1][1] == "chaser_applied"


@pytest.mark.asyncio
async def test_apply_chaser_intent_success_without_repetitions():
    manager = _FakeManager()
    ok = await apply_chaser(manager, {"chaser_name": "Downbeat plus two beats", "start_time_ms": 0})
    assert ok is True
    assert manager.events[-1][1] == "chaser_applied"


@pytest.mark.asyncio
async def test_start_chaser_intent_success():
    manager = _FakeManager()
    ok = await start_chaser(manager, {"chaser_name": "Downbeat plus two beats"})
    assert ok is True
    assert manager.events[-1][1] == "chaser_started"


@pytest.mark.asyncio
async def test_start_chaser_intent_success_without_repetitions():
    manager = _FakeManager()
    ok = await start_chaser(manager, {"chaser_name": "Downbeat plus two beats"})
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


def test_chaser_handlers_map_contains_full_names():
    assert "chaser.apply" in CHASER_HANDLERS
    assert "chaser.start" in CHASER_HANDLERS
    assert "chaser.stop" in CHASER_HANDLERS
    assert "chaser.list" in CHASER_HANDLERS
