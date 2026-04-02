import pytest

from backend.api.intents.cue.actions.apply_helper import apply_helper
from backend.api.intents.cue.actions.clear import clear_cue
from backend.api.intents.cue.actions.clear_all import clear_all_cues
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

    async def clear_cue_entries(self, from_time=0.0, to_time=None):
        if to_time is not None and to_time < from_time:
            return {"ok": False, "reason": "invalid_time_range"}
        return {"ok": True, "removed": 3, "remaining": 2}

    async def clear_all_cue_entries(self):
        return {"ok": True, "removed": 5, "remaining": 0}

    async def apply_cue_helper(self, helper_id, params=None):
        if helper_id in {"downbeats_and_beats", "parcan_echoes", "song_draft"}:
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
async def test_clear_cue_intent_success():
    manager = _FakeManager()

    ok = await clear_cue(manager, {"from_time": 4.0, "to_time": 9.0})

    assert ok is True
    assert manager.events[-1][1] == "cue_cleared"
    assert manager.events[-1][2]["removed"] == 3


@pytest.mark.asyncio
async def test_clear_all_cues_intent_success():
    manager = _FakeManager()

    ok = await clear_all_cues(manager, {})

    assert ok is True
    assert manager.events[-1][1] == "cue_cleared"
    assert manager.events[-1][2]["removed"] == 5
    assert manager.events[-1][2]["remaining"] == 0


@pytest.mark.asyncio
async def test_update_cue_intent_validation_error():
    manager = _FakeManager()

    ok = await update_cue(manager, {"index": "bad", "patch": {"duration": 1.0}})

    assert ok is False
    assert manager.events[-1][1] == "cue_update_failed"


@pytest.mark.asyncio
async def test_clear_cue_intent_validation_error():
    manager = _FakeManager()

    ok = await clear_cue(manager, {"from_time": "bad"})

    assert ok is False
    assert manager.events[-1][1] == "cue_clear_failed"


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
async def test_apply_helper_intent_accepts_params():
    manager = _FakeManager()
    manager.state_manager.current_song = type('MockSong', (), {'beats': None})()

    ok = await apply_helper(manager, {
        "helper_id": "parcan_echoes",
        "params": {"start_time_ms": 1200, "color": "#FF0000"},
    })

    assert ok is True
    assert manager.events[-1][1] == "cue_helper_applied"
    assert manager.events[-1][2]["helper_id"] == "parcan_echoes"


@pytest.mark.asyncio
async def test_apply_helper_intent_validation_error():
    manager = _FakeManager()

    ok = await apply_helper(manager, {"helper_id": ""})

    assert ok is False
    assert manager.events[-1][1] == "cue_helper_apply_failed"


@pytest.mark.asyncio
async def test_apply_helper_intent_invalid_params_error():
    manager = _FakeManager()
    manager.state_manager.current_song = type('MockSong', (), {'beats': None})()

    ok = await apply_helper(manager, {"helper_id": "parcan_echoes", "params": []})

    assert ok is False
    assert manager.events[-1][1] == "cue_helper_apply_failed"
    assert manager.events[-1][2]["reason"] == "invalid_helper_params"


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
async def test_apply_helper_intent_forwards_missing_artifacts():
    manager = _FakeManager()
    manager.state_manager.current_song = type("MockSong", (), {"beats": object()})()

    async def apply_cue_helper(helper_id, params=None):
        return {
            "ok": False,
            "reason": "features_unavailable",
            "helper_id": helper_id,
            "missing_artifacts": [
                {"artifact": "features_file", "path": "/tmp/meta/song/features.json"},
            ],
        }

    manager.state_manager.apply_cue_helper = apply_cue_helper

    ok = await apply_helper(manager, {"helper_id": "song_draft"})

    assert ok is False
    assert manager.events[-1][1] == "cue_helper_apply_failed"
    assert manager.events[-1][2]["missing_artifacts"] == [
        {"artifact": "features_file", "path": "/tmp/meta/song/features.json"},
    ]


@pytest.mark.asyncio
async def test_cue_handlers_map_contains_full_names():
    assert "cue.add" in CUE_HANDLERS
    assert "cue.update" in CUE_HANDLERS
    assert "cue.delete" in CUE_HANDLERS
    assert "cue.clear" in CUE_HANDLERS
    assert "cue.clear_all" in CUE_HANDLERS
    assert "cue.apply_helper" in CUE_HANDLERS
