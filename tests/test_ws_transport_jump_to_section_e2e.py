from types import SimpleNamespace

from fastapi.testclient import TestClient

import main as backend_main
from services.artnet import ArtNetService
from services.song_service import SongService
from store.state import StateManager

from backend.models.song.beats import Beats, Beat


def _fake_song(song_name: str):
    return SimpleNamespace(
        song_id=song_name,
        audio_url=f"/songs/{song_name}.mp3",
        meta=SimpleNamespace(duration=90.0, bpm=128.0),
        beats=Beats(beats=[
            Beat(time=0.0, beat=1, bar=0),
            Beat(time=0.5, beat=2, bar=0),
            Beat(time=1.0, beat=3, bar=0)
        ]),
        sections=SimpleNamespace(
            sections=[
                {"name": "Intro", "start_s": 0.0, "end_s": 12.0},
                {"name": "Verse", "start_s": 12.0, "end_s": 24.2},
                {"name": "Drop", "start_s": 24.21, "end_s": 40.0},
            ]
        ),
    )


def _read_until_type(ws, expected_type: str, max_reads: int = 8):
    for _ in range(max_reads):
        msg = ws.receive_json()
        if msg.get("type") == expected_type:
            return msg
    raise AssertionError(f"did not receive message type {expected_type}")


def test_ws_transport_jump_to_section_updates_playback_time(monkeypatch):
    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = _fake_song(song_name)
        self.song_length_seconds = 90.0
        self.timecode = 0.0

    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: ["fake-song"])
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)

    with TestClient(backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            initial = _read_until_type(ws, "snapshot")
            assert initial["state"]["playback"]["time_ms"] == 0

            ws.send_json(
                {
                    "type": "intent",
                    "req_id": "e2e-jump-section-1",
                    "name": "transport.jump_to_section",
                    "payload": {"section_index": 2},
                }
            )

            ws.send_json({"type": "hello"})
            refreshed = _read_until_type(ws, "snapshot")

            assert refreshed["state"]["playback"]["time_ms"] == 24210
            assert refreshed["state"]["playback"]["section_name"] == "Drop"