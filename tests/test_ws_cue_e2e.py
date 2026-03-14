import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main as backend_main
from services.artnet import ArtNetService
from services.song_service import SongService
from store.state import StateManager
from backend.models.cues import load_cue_sheet
from backend.models.song.beats import Beats


SONG_NAME = "Yonaka - Seize the Power"


def _cue_value(cues, index: int, key: str):
    return cues[index].get(key) if index < len(cues) else None


def _read_until_type(ws, expected_type: str, max_reads: int = 8):
    for _ in range(max_reads):
        msg = ws.receive_json()
        if msg.get("type") == expected_type:
            return msg
    raise AssertionError(f"did not receive message type {expected_type}")


@pytest.mark.e2e_real_file
def test_ws_cue_update_and_delete_persist_and_restore_real_file(request, monkeypatch):
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
        assert isinstance(baseline, list)
        assert len(baseline) >= 2

        updated_duration = float(baseline[0]["duration"]) + 0.25
        updated_name = "e2e-updated"

        with TestClient(backend_main.app) as client:
            with client.websocket_connect("/ws") as ws:
                initial = _read_until_type(ws, "snapshot")
                assert initial.get("type") == "snapshot"
                cues_initial = initial["state"].get("cues", [])
                assert len(cues_initial) >= 2

                ws.send_json(
                    {
                        "type": "intent",
                        "req_id": "e2e-cue-update-1",
                        "name": "cue.update",
                        "payload": {
                            "index": 0,
                            "patch": {"duration": updated_duration, "name": updated_name},
                        },
                    }
                )

                ws.send_json({"type": "hello"})
                refreshed = _read_until_type(ws, "snapshot")
                assert refreshed.get("type") == "snapshot"
                cues_refreshed = refreshed["state"].get("cues", [])
                assert _cue_value(cues_refreshed, 0, "duration") == updated_duration
                assert _cue_value(cues_refreshed, 0, "name") == updated_name

                ws.send_json(
                    {
                        "type": "intent",
                        "req_id": "e2e-cue-delete-1",
                        "name": "cue.delete",
                        "payload": {"index": 1},
                    }
                )

                ws.send_json({"type": "hello"})
                refreshed_after_delete = _read_until_type(ws, "snapshot")
                assert refreshed_after_delete.get("type") == "snapshot"
                cues_after_delete = refreshed_after_delete["state"].get("cues", [])
                assert len(cues_after_delete) == len(baseline) - 1

        persisted = json.loads(cues_path.read_text(encoding="utf-8"))
        assert len(persisted) == len(baseline) - 1
        assert _cue_value(persisted, 0, "duration") == updated_duration
        assert _cue_value(persisted, 0, "name") == updated_name
    finally:
        cues_path.write_bytes(original_bytes)
        assert cues_path.read_bytes() == original_bytes
