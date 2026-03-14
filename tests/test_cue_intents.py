import pytest

from backend.api.intents.cue.actions.delete import delete_cue
from backend.api.intents.cue.actions.update import update_cue
from backend.api.intents.cue.handlers import CUE_HANDLERS


class _FakeStateManager:
    async def update_cue_entry(self, index, payload):
        if index != 0:
            return {"ok": False, "reason": "cue_index_out_of_range"}
        return {"ok": True, "entry": {"index": index, **payload}}

    async def delete_cue_entry(self, index):
        if index != 0:
            return {"ok": False, "reason": "cue_index_out_of_range"}
        return {"ok": True, "entry": {"index": index}}


class _FakeManager:
    def __init__(self):
        self.state_manager = _FakeStateManager()
        self.events = []

    async def broadcast_event(self, level, message, data):
        self.events.append((level, message, data))


@pytest.mark.asyncio
async def test_update_cue_intent_success():
    manager = _FakeManager()

    ok = await update_cue(manager, {"index": 0, "patch": {"duration": 1.25}})

    assert ok is True
    assert manager.events[-1][1] == "cue_updated"


@pytest.mark.asyncio
async def test_delete_cue_intent_success():
    manager = _FakeManager()

    ok = await delete_cue(manager, {"index": 0})

    assert ok is True
    assert manager.events[-1][1] == "cue_deleted"


@pytest.mark.asyncio
async def test_update_cue_intent_validation_error():
    manager = _FakeManager()

    ok = await update_cue(manager, {"index": "bad", "patch": {"duration": 1.0}})

    assert ok is False
    assert manager.events[-1][1] == "cue_update_failed"


@pytest.mark.asyncio
async def test_cue_handlers_map_contains_full_names():
    assert "cue.add" in CUE_HANDLERS
    assert "cue.update" in CUE_HANDLERS
    assert "cue.delete" in CUE_HANDLERS
