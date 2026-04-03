from types import SimpleNamespace

from fastapi.testclient import TestClient

import main as backend_main
from backend.models.cues import CueEntry, CueSheet
from backend.models.song.beats import Beat, Beats
from services.artnet import ArtNetService
from services.song_service import SongService
from store.state import StateManager


def _fake_song(song_name: str):
    return SimpleNamespace(
        song_id=song_name,
        audio_url=f"/songs/{song_name}.mp3",
        meta=SimpleNamespace(duration=90.0, bpm=128.0 if song_name == "alpha-song" else 140.0),
        beats=Beats(beats=[Beat(time=0.0, beat=1, bar=0), Beat(time=0.5, beat=2, bar=0)]),
        sections=SimpleNamespace(
            sections=[
                {"name": "Intro", "start_s": 0.0, "end_s": 8.0},
                {"name": "Drop", "start_s": 8.0, "end_s": 16.0},
            ]
        ),
    )


def _read_until(ws, predicate, max_reads: int = 8):
    for _ in range(max_reads):
        message = ws.receive_json()
        if predicate(message):
            return message
    raise AssertionError("did not receive expected websocket message")


def _read_until_type(ws, expected_type: str, max_reads: int = 8):
    return _read_until(ws, lambda message: message.get("type") == expected_type, max_reads=max_reads)


def test_ws_song_list_and_load(monkeypatch):
    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = _fake_song(song_name)
        self.song_length_seconds = 90.0
        self.timecode = 0.0
        self.is_playing = False
        self.output_universe = bytearray(512)
        self.editor_universe = bytearray(512)
        self.cue_sheet = CueSheet(
            song_filename=song_name,
            entries=[
                CueEntry(
                    time=0.0,
                    fixture_id="fixture-a" if song_name == "alpha-song" else "fixture-b",
                    effect="flash",
                    duration=0.5,
                    data={"color": song_name},
                )
            ],
        )

    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: ["alpha-song", "beta-song"])
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(ArtNetService, "set_continuous_send", _noop_async)
    monkeypatch.setattr(ArtNetService, "update_universe", _noop_async)

    with TestClient(backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            initial = _read_until_type(ws, "snapshot")
            assert initial["state"]["song"]["filename"] == "alpha-song"

            ws.send_json(
                {
                    "type": "intent",
                    "req_id": "song-list-1",
                    "name": "song.list",
                    "payload": {},
                }
            )

            list_event = _read_until(
                ws,
                lambda message: message.get("type") == "event" and message.get("message") == "song_list",
            )
            assert list_event["data"] == {"songs": ["alpha-song", "beta-song"]}

            ws.send_json(
                {
                    "type": "intent",
                    "req_id": "song-load-1",
                    "name": "song.load",
                    "payload": {"filename": "beta-song"},
                }
            )

            load_event = _read_until(
                ws,
                lambda message: message.get("type") == "event" and message.get("message") == "song_loaded",
            )
            assert load_event["data"] == {"filename": "beta-song"}

            patch = _read_until(ws, lambda message: message.get("type") == "patch")
            changes = {tuple(change["path"]): change["value"] for change in patch["changes"]}

            assert changes[("song",)]["filename"] == "beta-song"
            assert changes[("song",)]["bpm"] == 140.0
            assert changes[("song",)]["beats"] == [
                {"time": 0.0, "beat": 1, "bar": 0, "bass": None, "chord": None, "type": "downbeat"},
                {"time": 0.5, "beat": 2, "bar": 0, "bass": None, "chord": None, "type": "beat"},
            ]
            assert changes[("playback",)]["time_ms"] == 0
            assert changes[("cues",)][0]["fixture_id"] == "fixture-b"

            ws.send_json({"type": "hello"})
            refreshed = _read_until_type(ws, "snapshot")
            assert refreshed["state"]["song"]["filename"] == "beta-song"