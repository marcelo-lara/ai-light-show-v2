import pytest

from backend.api.intents.cue.actions.apply_helper import apply_helper
from backend.api.intents.cue.actions.delete import delete_cue
from backend.api.intents.cue.actions.update import update_cue
from backend.api.intents.cue.handlers import CUE_HANDLERS


class _FakeStateManager:
    def __init__(self):
        self.current_song = None

    async def update_cue_entry(self, index, payload):
        if index != 0:
            return {"ok": False, "reason": "cue_index_out_of_range"}
        return {"ok": True, "entry": {"index": index, **payload}}

    async def delete_cue_entry(self, index):
        if index != 0:
            return {"ok": False, "reason": "cue_index_out_of_range"}
        return {"ok": True, "entry": {"index": index}}

    async def apply_cue_helper(self, helper_id):
        if helper_id == "downbeats_and_beats":
            return {"ok": True, "generated": 5, "replaced": 2, "skipped": 0}
        return {"ok": False, "reason": "unknown_helper_id", "helper_id": helper_id}


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
async def test_apply_helper_intent_success():
    manager = _FakeManager()
    
    # Mock song with beats
    from models.song.beats import Beat
    mock_beats = [Beat(time=0.0, beat=1, bar=1), Beat(time=1.0, beat=2, bar=1)]
    mock_beats_obj = type('MockBeats', (), {'beats': mock_beats})()
    manager.state_manager.current_song = type('MockSong', (), {'beats': mock_beats_obj})()

    ok = await apply_helper(manager, {"helper_id": "downbeats_and_beats"})

    assert ok is True
    assert manager.events[-1][1] == "cue_helper_applied"
    assert manager.events[-1][2]["helper_id"] == "downbeats_and_beats"
    assert manager.events[-1][2]["generated"] == 5
    assert manager.events[-1][2]["replaced"] == 2
    assert manager.events[-1][2]["skipped"] == 0


@pytest.mark.asyncio
async def test_apply_helper_intent_validation_error():
    manager = _FakeManager()

    ok = await apply_helper(manager, {"helper_id": ""})

    assert ok is False
    assert manager.events[-1][1] == "cue_helper_apply_failed"


@pytest.mark.asyncio
async def test_apply_helper_intent_unknown_helper():
    manager = _FakeManager()
    
    # Mock song with beats
    from models.song.beats import Beat
    mock_beats = [Beat(time=0.0, beat=1, bar=1)]
    mock_beats_obj = type('MockBeats', (), {'beats': mock_beats})()
    manager.state_manager.current_song = type('MockSong', (), {'beats': mock_beats_obj})()

    ok = await apply_helper(manager, {"helper_id": "unknown"})

    assert ok is False
    assert manager.events[-1][1] == "cue_helper_apply_failed"


@pytest.mark.asyncio
async def test_cue_handlers_map_contains_full_names():
    assert "cue.add" in CUE_HANDLERS
    assert "cue.update" in CUE_HANDLERS
    assert "cue.delete" in CUE_HANDLERS
    assert "cue.apply_helper" in CUE_HANDLERS
    assert "cue.apply_helper" in CUE_HANDLERS
