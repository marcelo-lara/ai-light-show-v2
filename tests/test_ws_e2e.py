import asyncio
import json
from pathlib import Path
import pytest

from backend.api.websocket import WebSocketManager
from backend.store.state import StateManager


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_json(self, message):
        self.sent.append(message)


class FakeSongService:
    def __init__(self, songs_path: Path, meta_path: Path):
        self.songs_path = songs_path
        self.meta_path = meta_path


class DummyState:
    # minimal stub used only to satisfy WebSocketManager constructor
    def __init__(self):
        self.fixtures = []
        self.cue_sheet = None
        self.current_song = None


class DummyArtNet:
    async def update_universe(self, universe):
        return None


class RecorderArtNet:
    def __init__(self):
        self.updates = []

    async def update_universe(self, universe):
        self.updates.append(bytes(universe))


class PreviewStateStub:
    def __init__(self, preview_lifetime: float = 0.03):
        self.fixtures = []
        self.cue_sheet = None
        self.current_song = None
        self.song_length_seconds = 0.0
        self.is_playing = False
        self.preview_active = False
        self.preview_request_id = None
        self.preview_end_event = asyncio.Event()
        self.preview_lifetime = float(preview_lifetime)
        self.output_tick = 0
        self.persisted_tick = 0

    async def get_is_playing(self):
        return bool(self.is_playing)

    async def get_status(self):
        return {
            "isPlaying": bool(self.is_playing),
            "previewActive": bool(self.preview_active),
            "preview": {
                "requestId": self.preview_request_id,
                "fixtureId": "fixture-1",
                "effect": "flash",
                "duration": 0.05,
            }
            if self.preview_active
            else None,
        }

    async def set_playback_state(self, playing):
        self.is_playing = bool(playing)
        if self.is_playing:
            self.preview_active = False
            self.preview_request_id = None
            self.preview_end_event.set()

    async def start_preview_effect(self, fixture_id, effect, duration, data, request_id=None):
        if self.is_playing:
            return {"ok": False, "reason": "playback_active"}

        rid = request_id or "preview-req-1"
        self.preview_active = True
        self.preview_request_id = rid
        self.preview_end_event = asyncio.Event()

        async def finish_preview_soon():
            await asyncio.sleep(self.preview_lifetime)
            self.persisted_tick = self.output_tick
            self.preview_active = False
            self.preview_request_id = None
            self.preview_end_event.set()

        asyncio.create_task(finish_preview_soon())

        return {
            "ok": True,
            "requestId": rid,
            "fixtureId": fixture_id,
            "effect": effect,
            "duration": duration,
        }

    async def wait_for_preview_end(self, request_id):
        await self.preview_end_event.wait()

    async def get_output_universe(self):
        universe = bytearray(512)
        if self.preview_active:
            self.output_tick = (self.output_tick + 1) % 256
            universe[16] = self.output_tick
            self.persisted_tick = self.output_tick
            return universe

        if self.persisted_tick:
            universe[16] = self.persisted_tick
        return universe


@pytest.mark.asyncio
async def test_save_sections_persists_and_broadcasts(tmp_path):
    backend_dir = tmp_path / "backend"
    fixtures_dir = backend_dir / "fixtures"
    fixtures_dir.mkdir(parents=True)
    meta_dir = backend_dir / "meta"
    meta_dir.mkdir()

    fixtures_path = fixtures_dir / "fixtures.json"
    fixtures_path.write_text(json.dumps([]))

    state = StateManager(backend_dir)
    await state.load_fixtures(fixtures_path)

    manager = WebSocketManager(state, DummyArtNet(), FakeSongService(str(tmp_path), str(meta_dir)))
    ws_sender = FakeWS()
    ws_observer = FakeWS()
    manager.active_connections.extend([ws_sender, ws_observer])

    # Create initial metadata
    song_meta = meta_dir / "test_song.json"
    song_meta.write_text(json.dumps({
        "filename": "test_song.mp3",
        "length": 180,
        "hints": {"drums": []},
        "parts": {}
    }))

    await state.load_song("test_song")

    await manager.handle_message(
        ws_sender,
        json.dumps({
            "type": "save_sections",
            "sections": [
                {"name": "Intro", "start": 0, "end": 30},
                {"name": "Verse", "start": 30, "end": 60}
            ],
        }),
    )

    save_results = [msg for msg in ws_sender.sent if msg.get("type") == "sections_save_result"]
    assert save_results
    assert save_results[-1].get("ok") is True

    broadcast_events = [msg for msg in ws_observer.sent if msg.get("type") == "sections_updated"]
    assert broadcast_events

    # Check persisted
    persisted = json.loads(song_meta.read_text())
    assert persisted["parts"]["Intro"] == [0.0, 30.0]
    assert persisted["parts"]["Verse"] == [30.0, 60.0]


@pytest.mark.asyncio
async def test_preview_rejected_when_playback_active(tmp_path):
    state = PreviewStateStub()
    manager = WebSocketManager(state, DummyArtNet(), FakeSongService(str(tmp_path), str(tmp_path)))
    ws = FakeWS()
    manager.active_connections.append(ws)

    await manager.handle_message(ws, json.dumps({"type": "playback", "playing": True}))
    await manager.handle_message(
        ws,
        json.dumps(
            {
                "type": "preview_effect",
                "fixture_id": "fixture-1",
                "effect": "flash",
                "duration": 1.0,
                "data": {},
            }
        ),
    )

    preview_messages = [msg for msg in ws.sent if msg.get("type") == "preview_status"]
    assert preview_messages
    assert preview_messages[-1].get("active") is False
    assert preview_messages[-1].get("reason") == "playback_active"


@pytest.mark.asyncio
async def test_preview_broadcasts_start_and_end_status(tmp_path):
    state = PreviewStateStub()
    manager = WebSocketManager(state, DummyArtNet(), FakeSongService(str(tmp_path), str(tmp_path)))

    ws1 = FakeWS()
    ws2 = FakeWS()
    manager.active_connections.extend([ws1, ws2])

    await manager.handle_message(
        ws1,
        json.dumps(
            {
                "type": "preview_effect",
                "request_id": "preview-abc",
                "fixture_id": "fixture-1",
                "effect": "flash",
                "duration": 0.05,
                "data": {},
            }
        ),
    )

    await asyncio.sleep(0.12)

    ws1_preview_events = [msg for msg in ws1.sent if msg.get("type") == "preview_status"]
    ws2_preview_events = [msg for msg in ws2.sent if msg.get("type") == "preview_status"]

    assert any(msg.get("active") is True and msg.get("request_id") == "preview-abc" for msg in ws1_preview_events)
    assert any(msg.get("active") is True and msg.get("request_id") == "preview-abc" for msg in ws2_preview_events)
    assert any(msg.get("active") is False and msg.get("request_id") == "preview-abc" for msg in ws1_preview_events)
    assert any(msg.get("active") is False and msg.get("request_id") == "preview-abc" for msg in ws2_preview_events)

    ws1_status_events = [msg for msg in ws1.sent if msg.get("type") == "status"]
    assert any(event.get("status", {}).get("previewActive") is True for event in ws1_status_events)
    assert any(event.get("status", {}).get("previewActive") is False for event in ws1_status_events)


@pytest.mark.asyncio
async def test_preview_streams_temporary_canvas_to_artnet(tmp_path):
    state = PreviewStateStub(preview_lifetime=0.12)
    artnet = RecorderArtNet()
    manager = WebSocketManager(state, artnet, FakeSongService(str(tmp_path), str(tmp_path)))

    ws = FakeWS()
    manager.active_connections.append(ws)

    await manager.handle_message(
        ws,
        json.dumps(
            {
                "type": "preview_effect",
                "request_id": "preview-stream-1",
                "fixture_id": "parcan_l",
                "effect": "flash",
                "duration": 0.2,
                "data": {},
            }
        ),
    )

    await asyncio.sleep(0.25)

    assert len(artnet.updates) >= 2
    unique_frames = {packet[16] for packet in artnet.updates}
    assert len(unique_frames) >= 2
    assert artnet.updates[-1][16] == state.persisted_tick
    assert artnet.updates[-1][16] > 0


@pytest.mark.asyncio
async def test_initial_state_includes_pois(tmp_path):
    backend_dir = tmp_path / "backend"
    fixtures_dir = backend_dir / "fixtures"
    fixtures_dir.mkdir(parents=True)

    fixtures_path = fixtures_dir / "fixtures.json"
    fixtures_path.write_text(
        json.dumps([
            {
                "id": "head_1",
                "name": "Head 1",
                "type": "moving_head",
                "location": {"x": 0.0, "y": 0.0, "z": 0.0},
                "channels": {"pan_msb": 1, "pan_lsb": 2, "tilt_msb": 3, "tilt_lsb": 4},
                "presets": [],
                "poi_targets": {},
                "current_values": {},
                "effects": [],
                "arm": {},
                "meta": {},
            }
        ])
    )

    pois_path = fixtures_dir / "pois.json"
    pois_path.write_text(json.dumps([
        {"id": "piano", "name": "Piano", "location": {"x": 0.5, "y": 0.5, "z": 0.0}}
    ]))

    state = StateManager(backend_dir)
    await state.load_pois(pois_path)
    await state.load_fixtures(fixtures_path)

    manager = WebSocketManager(state, DummyArtNet(), FakeSongService(str(tmp_path), str(tmp_path)))
    ws = FakeWS()
    await manager.send_initial_state(ws)

    assert ws.sent
    message = ws.sent[-1]
    assert message.get("type") == "initial"
    assert message.get("pois") == [{"id": "piano", "name": "Piano", "location": {"x": 0.5, "y": 0.5, "z": 0.0}}]


@pytest.mark.asyncio
async def test_save_poi_target_persists_and_broadcasts(tmp_path):
    backend_dir = tmp_path / "backend"
    fixtures_dir = backend_dir / "fixtures"
    fixtures_dir.mkdir(parents=True)

    fixtures_path = fixtures_dir / "fixtures.json"
    fixtures_path.write_text(
        json.dumps([
            {
                "id": "head_1",
                "name": "Head 1",
                "type": "moving_head",
                "location": {"x": 0.0, "y": 0.0, "z": 0.0},
                "channels": {"pan_msb": 1, "pan_lsb": 2, "tilt_msb": 3, "tilt_lsb": 4},
                "presets": [{"name": "Piano", "poi_id": "piano"}],
                "poi_targets": {},
                "current_values": {},
                "effects": ["seek"],
                "arm": {},
                "meta": {},
            }
        ])
    )

    pois_path = fixtures_dir / "pois.json"
    pois_path.write_text(json.dumps([
        {"id": "piano", "name": "Piano", "location": {"x": 0.5, "y": 0.5, "z": 0.0}}
    ]))

    state = StateManager(backend_dir)
    await state.load_pois(pois_path)
    await state.load_fixtures(fixtures_path)

    manager = WebSocketManager(state, DummyArtNet(), FakeSongService(str(tmp_path), str(tmp_path)))
    ws_sender = FakeWS()
    ws_observer = FakeWS()
    manager.active_connections.extend([ws_sender, ws_observer])

    await manager.handle_message(
        ws_sender,
        json.dumps({
            "type": "save_poi_target",
            "fixture_id": "head_1",
            "poi_id": "piano",
            "pan": 12345,
            "tilt": 678,
        }),
    )

    save_results = [msg for msg in ws_sender.sent if msg.get("type") == "save_poi_target_result"]
    assert save_results
    assert save_results[-1].get("ok") is True

    broadcast_events = [msg for msg in ws_observer.sent if msg.get("type") == "fixtures_updated"]
    assert broadcast_events

    updated_fixture = next((f for f in state.fixtures if f.id == "head_1"), None)
    assert updated_fixture is not None
    assert updated_fixture.poi_targets.get("piano") == {"pan": 12345, "tilt": 678}

    persisted = json.loads(fixtures_path.read_text())
    assert persisted[0]["poi_targets"]["piano"] == {"pan": 12345, "tilt": 678}
