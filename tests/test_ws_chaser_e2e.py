# pyright: reportMissingImports=false

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main as backend_main
from backend.models.cues import load_cue_sheet
from backend.models.song.beats import Beats
from services.artnet import ArtNetService
from services.song_service import SongService
from store.state import StateManager


SONG_NAME = "Yonaka - Seize the Power"
CHASER_ID = "downbeats_and_beats"


def _read_until_type(ws, expected_type: str, max_reads: int = 12):
    for _ in range(max_reads):
        msg = ws.receive_json()
        if msg.get("type") == expected_type:
            return msg
    raise AssertionError(f"did not receive message type {expected_type}")


def _read_until_event(ws, expected_message: str, max_reads: int = 12):
    for _ in range(max_reads):
        msg = ws.receive_json()
        if msg.get("type") == "event" and msg.get("message") == expected_message:
            return msg
    raise AssertionError(f"did not receive event {expected_message}")


@pytest.mark.e2e_real_file
def test_ws_chaser_apply_persists_and_restores_real_file(request, monkeypatch):
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
        self.cue_sheet = load_cue_sheet(self.cues_path, song_name)

    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: [SONG_NAME])
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)

    workspace_root = Path(__file__).resolve().parents[1]
    cues_path = workspace_root / "backend" / "cues" / f"{SONG_NAME}.json"
    original_bytes = cues_path.read_bytes()

    try:
        baseline = json.loads(original_bytes.decode("utf-8"))
        baseline_count = len(baseline)

        with TestClient(backend_main.app) as client:
            with client.websocket_connect("/ws") as ws:
                initial = _read_until_type(ws, "snapshot")
                assert initial.get("type") == "snapshot"
                assert isinstance(initial["state"].get("chasers"), list)

                ws.send_json(
                    {
                        "type": "intent",
                        "req_id": "e2e-chaser-apply-1",
                        "name": "chaser.apply",
                        "payload": {
                            "chaser_id": CHASER_ID,
                            "start_time_ms": 0,
                            "repetitions": 1,
                        },
                    }
                )

                evt = _read_until_event(ws, "chaser_applied")
                assert evt["data"]["chaser_id"] == CHASER_ID
                assert evt["data"]["entry"]["chaser_id"] == CHASER_ID

                ws.send_json({"type": "hello"})
                refreshed = _read_until_type(ws, "snapshot")
                cues = refreshed["state"].get("cues", [])
                assert len(cues) >= baseline_count
                assert any(item.get("chaser_id") == CHASER_ID for item in cues)

        persisted = json.loads(cues_path.read_text(encoding="utf-8"))
        assert any(item.get("chaser_id") == CHASER_ID for item in persisted)
    finally:
        cues_path.write_bytes(original_bytes)
        assert cues_path.read_bytes() == original_bytes


@pytest.mark.e2e_real_file
def test_ws_chaser_start_and_stop_event_flow(request, monkeypatch):
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
        self.cue_sheet = load_cue_sheet(self.cues_path, song_name)

    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: [SONG_NAME])
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)

    workspace_root = Path(__file__).resolve().parents[1]
    cues_path = workspace_root / "backend" / "cues" / f"{SONG_NAME}.json"
    original_bytes = cues_path.read_bytes()

    try:
        with TestClient(backend_main.app) as client:
            with client.websocket_connect("/ws") as ws:
                initial = _read_until_type(ws, "snapshot")
                assert initial.get("type") == "snapshot"

                ws.send_json(
                    {
                        "type": "intent",
                        "req_id": "e2e-chaser-start-1",
                        "name": "chaser.start",
                        "payload": {
                            "chaser_id": CHASER_ID,
                            "start_time_ms": 0,
                            "repetitions": 1,
                        },
                    }
                )

                started = _read_until_event(ws, "chaser_started")
                instance_id = str((started.get("data") or {}).get("instance_id") or "")
                assert instance_id

                ws.send_json(
                    {
                        "type": "intent",
                        "req_id": "e2e-chaser-stop-1",
                        "name": "chaser.stop",
                        "payload": {"instance_id": instance_id},
                    }
                )

                stopped = _read_until_event(ws, "chaser_stopped")
                assert (stopped.get("data") or {}).get("instance_id") == instance_id
    finally:
        cues_path.write_bytes(original_bytes)
        assert cues_path.read_bytes() == original_bytes
