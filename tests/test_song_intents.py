import pytest

from backend.api.intents.song.actions.list import list_songs
from backend.api.intents.song.actions.hints_create import create_human_hint
from backend.api.intents.song.actions.hints_delete import delete_human_hint
from backend.api.intents.song.actions.hints_update import update_human_hint
from backend.api.intents.song.actions.load import load_song
from backend.api.intents.song.handlers import SONG_HANDLERS


class _FakeSongService:
    def __init__(self, songs):
        self._songs = list(songs)

    def list_songs(self):
        return list(self._songs)


class _FakeStateManager:
    def __init__(self):
        self.loaded = []
        self.output_universe = bytearray(512)
        self.created_hints = []
        self.updated_hints = []
        self.deleted_hints = []

    async def load_song(self, filename):
        self.loaded.append(filename)

    async def get_output_universe(self):
        return bytearray(self.output_universe)

    async def create_human_hint(self, payload):
        self.created_hints.append(dict(payload))
        return {"ok": True, "hint": {"id": "ui_001", **payload}}

    async def update_human_hint(self, hint_id, patch):
        self.updated_hints.append((hint_id, dict(patch)))
        return {"ok": True, "hint": {"id": hint_id, **patch}}

    async def delete_human_hint(self, hint_id):
        self.deleted_hints.append(hint_id)
        return {"ok": True, "id": hint_id}


class _FakeArtNetService:
    def __init__(self):
        self.continuous = []
        self.universes = []

    async def set_continuous_send(self, continuous):
        self.continuous.append(bool(continuous))

    async def update_universe(self, universe):
        self.universes.append(bytearray(universe))


class _FakeManager:
    def __init__(self, songs):
        self.song_service = _FakeSongService(songs)
        self.state_manager = _FakeStateManager()
        self.artnet_service = _FakeArtNetService()
        self.events = []
        self.stop_calls = 0

    async def broadcast_event(self, level, message, data=None):
        self.events.append((level, message, data))

    async def stop_playback_ticker(self):
        self.stop_calls += 1


@pytest.mark.asyncio
async def test_list_songs_emits_song_list_event():
    manager = _FakeManager(["beta", "alpha"])

    ok = await list_songs(manager, {})

    assert ok is False
    assert manager.events == [("info", "song_list", {"songs": ["beta", "alpha"]})]


@pytest.mark.asyncio
async def test_load_song_success_updates_runtime_outputs():
    manager = _FakeManager(["alpha", "beta"])

    ok = await load_song(manager, {"filename": "beta"})

    assert ok is True
    assert manager.state_manager.loaded == ["beta"]
    assert manager.stop_calls == 1
    assert manager.artnet_service.continuous == [False]
    assert len(manager.artnet_service.universes) == 1
    assert manager.events[-1] == ("info", "song_loaded", {"filename": "beta"})


@pytest.mark.asyncio
async def test_load_song_rejects_missing_filename():
    manager = _FakeManager(["alpha"])

    ok = await load_song(manager, {})

    assert ok is False
    assert manager.state_manager.loaded == []
    assert manager.events[-1] == ("error", "song_load_failed", {"reason": "missing_filename"})


@pytest.mark.asyncio
async def test_load_song_rejects_unknown_song():
    manager = _FakeManager(["alpha"])

    ok = await load_song(manager, {"filename": "beta"})

    assert ok is False
    assert manager.state_manager.loaded == []
    assert manager.events[-1] == (
        "error",
        "song_load_failed",
        {"reason": "unknown_song", "filename": "beta", "songs": ["alpha"]},
    )


@pytest.mark.asyncio
async def test_load_song_reports_runtime_error():
    manager = _FakeManager(["alpha"])

    async def _failing_load_song(filename):
        raise ValueError(f"bad song: {filename}")

    manager.state_manager.load_song = _failing_load_song

    ok = await load_song(manager, {"filename": "alpha"})

    assert ok is False
    assert manager.stop_calls == 0
    assert manager.artnet_service.continuous == []
    assert manager.events[-1] == (
        "error",
        "song_load_failed",
        {"reason": "load_failed", "filename": "alpha", "error": "bad song: alpha"},
    )


def test_song_handlers_map_contains_full_names():
    assert "song.list" in SONG_HANDLERS
    assert "song.load" in SONG_HANDLERS
    assert "song.hints.create" in SONG_HANDLERS
    assert "song.hints.update" in SONG_HANDLERS
    assert "song.hints.delete" in SONG_HANDLERS


@pytest.mark.asyncio
async def test_create_human_hint_emits_success_event():
    manager = _FakeManager(["alpha"])

    ok = await create_human_hint(manager, {"start_time": 1.0, "end_time": 2.0, "title": "A", "summary": "B", "lighting_hint": "C"})

    assert ok is True
    assert manager.state_manager.created_hints == [{"start_time": 1.0, "end_time": 2.0, "title": "A", "summary": "B", "lighting_hint": "C"}]
    assert manager.events[-1][1] == "song_hint_created"


@pytest.mark.asyncio
async def test_update_human_hint_rejects_missing_patch():
    manager = _FakeManager(["alpha"])

    ok = await update_human_hint(manager, {"id": "ui_001"})

    assert ok is False
    assert manager.state_manager.updated_hints == []
    assert manager.events[-1] == ("error", "song_hint_update_failed", {"reason": "missing_patch", "id": "ui_001"})


@pytest.mark.asyncio
async def test_update_human_hint_accepts_start_time_patch():
    manager = _FakeManager(["alpha"])

    ok = await update_human_hint(manager, {"id": "ui_001", "patch": {"start_time": 1.5, "end_time": 2.0}})

    assert ok is True
    assert manager.state_manager.updated_hints == [("ui_001", {"start_time": 1.5, "end_time": 2.0})]
    assert manager.events[-1][1] == "song_hint_updated"


@pytest.mark.asyncio
async def test_delete_human_hint_emits_success_event():
    manager = _FakeManager(["alpha"])

    ok = await delete_human_hint(manager, {"id": "ui_001"})

    assert ok is True
    assert manager.state_manager.deleted_hints == ["ui_001"]
    assert manager.events[-1] == ("info", "song_hint_deleted", {"ok": True, "id": "ui_001"})