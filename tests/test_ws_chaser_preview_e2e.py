# pyright: reportMissingImports=false

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main as backend_main
from backend.models.song.beats import Beats
from services.artnet import ArtNetService
from services.song_service import SongService
from store.state import StateManager


SONG_NAME = "Yonaka - Seize the Power"
CHASER_NAME = "Downbeat plus two beats"


def _read_until_type(ws, expected_type: str, max_reads: int = 20):
    for _ in range(max_reads):
        msg = ws.receive_json()
        if msg.get("type") == expected_type:
            return msg
    raise AssertionError(f"did not receive message type {expected_type}")


def _read_until_event(ws, expected_message: str, max_reads: int = 20):
    for _ in range(max_reads):
        msg = ws.receive_json()
        if msg.get("type") == "event" and msg.get("message") == expected_message:
            return msg
    raise AssertionError(f"did not receive event {expected_message}")


@pytest.mark.e2e_real_file
def test_ws_chaser_preview_no_persist(request, monkeypatch):
    selected_markexpr = (request.config.getoption("-m") or "").strip()
    if "e2e_real_file" not in selected_markexpr:
        pytest.skip("opt-in only; run with -m e2e_real_file")

    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = SimpleNamespace(
            song_id=song_name,
            audio_url=f"/songs/{song_name}.mp3",
            meta=SimpleNamespace(duration=90.0, bpm=120.0),
            beats=Beats(beats=[]),
            sections=SimpleNamespace(sections=[]),
        )
        self.song_length_seconds = 90.0

    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: [SONG_NAME])
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)

    with TestClient(backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            initial = _read_until_type(ws, "snapshot")
            baseline_count = len(initial["state"].get("cues", []))

            ws.send_json(
                {
                    "type": "intent",
                    "req_id": "e2e-chaser-preview-1",
                    "name": "chaser.preview",
                    "payload": {
                        "chaser_name": CHASER_NAME,
                        "start_time_ms": 0,
                        "repetitions": 2,
                    },
                }
            )
            started = _read_until_event(ws, "chaser_preview_started")
            assert started["data"]["chaser_name"] == CHASER_NAME

            ws.send_json(
                {
                    "type": "intent",
                    "req_id": "e2e-chaser-preview-stop-1",
                    "name": "chaser.stop_preview",
                    "payload": {},
                }
            )
            _read_until_event(ws, "chaser_preview_stopped")

            ws.send_json({"type": "hello"})
            refreshed = _read_until_type(ws, "snapshot")
            assert len(refreshed["state"].get("cues", [])) == baseline_count
