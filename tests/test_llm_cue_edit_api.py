from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.intents.llm.cue_edit_api import router


class _FakeStateManager:
    def __init__(self, is_playing: bool = False):
        self._is_playing = is_playing
        self.current_song = SimpleNamespace(song_id="test-song")
        self.entries = []

    async def get_is_playing(self):
        return self._is_playing

    async def add_effect_cue_entry(self, time, fixture_id, effect, duration, data):
        entry = {"time": time, "fixture_id": fixture_id, "effect": effect, "duration": duration, "data": data}
        self.entries.append(entry)
        return {"ok": True, "entry": entry}

    def get_cue_entries(self):
        return list(self.entries)


class _FakeManager:
    def __init__(self, is_playing: bool = False):
        self.state_manager = _FakeStateManager(is_playing=is_playing)
        self.events = []
        self.broadcasts = 0

    async def broadcast_event(self, level, message, data=None):
        self.events.append((level, message, data))

    async def _schedule_broadcast(self):
        self.broadcasts += 1


def _build_client(manager: _FakeManager) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.ws_manager = manager
    return TestClient(app)


def test_llm_add_cue_route_returns_updated_cue_sheet():
    manager = _FakeManager()
    with _build_client(manager) as client:
        response = client.post(
            "/llm/actions/cues/add",
            json={"payload": {"time": 12.5, "fixture_id": "head_1", "effect": "strobe", "duration": 2.0, "data": {"speed": 180}}},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert body["data"]["intent"] == "cue.add"
    assert body["data"]["event"]["message"] == "cue_added"
    assert body["data"]["cue_sheet"]["entry_count"] == 1
    assert body["data"]["cue_sheet"]["entries"][0]["index"] == 0
    assert manager.events[-1][1] == "cue_added"
    assert manager.broadcasts == 1


def test_llm_add_cue_route_rejects_when_show_running():
    manager = _FakeManager(is_playing=True)
    with _build_client(manager) as client:
        response = client.post("/llm/actions/cues/add", json={"payload": {"time": 12.5}})

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is False
    assert body["error"]["message"] == "llm_cue_edit_rejected"
    assert body["error"]["data"]["reason"] == "show_running"
    assert manager.events[-1][1] == "llm_cue_edit_rejected"
    assert manager.broadcasts == 0