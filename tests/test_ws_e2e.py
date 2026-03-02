import json
from types import SimpleNamespace
from typing import Any, cast

import pytest

from backend.api.websocket import WebSocketManager


class FakeWS:
    def __init__(self):
        self.sent = []

    async def accept(self):
        return None

    async def send_json(self, message):
        self.sent.append(message)


class DummySongService:
    pass


class DummyArtNet:
    def __init__(self):
        self.frames = []
        self.continuous = []

    async def update_universe(self, universe):
        self.frames.append(bytes(universe))

    async def set_continuous_send(self, enabled: bool):
        self.continuous.append(bool(enabled))


class StateStub:
    def __init__(self):
        self.timecode = 0.0
        self.is_playing = False
        self.universe = bytearray(512)
        self.fixtures = [
            SimpleNamespace(
                id="fixture-1",
                name="Fixture 1",
                type="rgb",
                channels={"dimmer": 1, "red": 2, "green": 3, "blue": 4},
                current_values={},
            )
        ]
        self.current_song = SimpleNamespace(
            metadata=SimpleNamespace(
                bpm=128,
                parts={"Intro": [0.0, 10.0], "Drop": [10.0, 20.0]},
            )
        )

    async def get_status(self):
        return {
            "isPlaying": self.is_playing,
            "previewActive": False,
            "preview": None,
        }

    async def get_timecode(self):
        return float(self.timecode)

    async def get_output_universe(self):
        return bytearray(self.universe)

    async def set_playback_state(self, is_playing: bool):
        self.is_playing = bool(is_playing)

    async def seek_timecode(self, timecode: float):
        self.timecode = float(timecode)

    async def update_dmx_channel(self, channel: int, value: int):
        if 1 <= int(channel) <= 512:
            self.universe[int(channel) - 1] = max(0, min(255, int(value)))
            return True
        return False

    async def start_preview_effect(self, fixture_id: str, effect: str, duration: float, data, request_id=None):
        return {
            "ok": True,
            "requestId": request_id or "preview-1",
            "fixtureId": fixture_id,
            "effect": effect,
            "duration": duration,
        }


@pytest.mark.asyncio
async def test_connect_and_hello_emit_snapshots():
    state = StateStub()
    artnet = DummyArtNet()
    manager = WebSocketManager(cast(Any, state), cast(Any, artnet), cast(Any, DummySongService()))
    ws = FakeWS()

    await manager.connect(cast(Any, ws))
    assert ws.sent[-1]["type"] == "snapshot"
    first_seq = ws.sent[-1]["seq"]

    await manager.handle_message(cast(Any, ws), json.dumps({"type": "hello", "client": "uix-ui", "version": "0.1"}))
    assert ws.sent[-1]["type"] == "snapshot"
    assert ws.sent[-1]["seq"] > first_seq


@pytest.mark.asyncio
async def test_fixture_set_arm_broadcasts_patch():
    state = StateStub()
    artnet = DummyArtNet()
    manager = WebSocketManager(cast(Any, state), cast(Any, artnet), cast(Any, DummySongService()))
    ws = FakeWS()

    await manager.connect(cast(Any, ws))
    ws.sent.clear()

    await manager.handle_message(
        cast(Any, ws),
        json.dumps(
            {
                "type": "intent",
                "req_id": "req-1",
                "name": "fixture.set_arm",
                "payload": {"fixture_id": "fixture-1", "armed": False},
            }
        ),
    )

    patch = next(msg for msg in ws.sent if msg.get("type") == "patch")
    fixtures = next(ch["value"] for ch in patch["changes"] if ch["path"] == ["fixtures"])
    assert fixtures["fixture-1"]["armed"] is False


@pytest.mark.asyncio
async def test_fixture_set_values_updates_output_and_artnet():
    state = StateStub()
    artnet = DummyArtNet()
    manager = WebSocketManager(cast(Any, state), cast(Any, artnet), cast(Any, DummySongService()))
    ws = FakeWS()

    await manager.connect(cast(Any, ws))
    ws.sent.clear()

    await manager.handle_message(
        cast(Any, ws),
        json.dumps(
            {
                "type": "intent",
                "req_id": "req-2",
                "name": "fixture.set_values",
                "payload": {"fixture_id": "fixture-1", "values": {"dimmer": 200}},
            }
        ),
    )

    assert artnet.frames
    patch = next(msg for msg in ws.sent if msg.get("type") == "patch")
    fixtures = next(ch["value"] for ch in patch["changes"] if ch["path"] == ["fixtures"])
    assert fixtures["fixture-1"]["channels"]["dimmer"] == 200


@pytest.mark.asyncio
async def test_llm_prompt_emits_stream_events():
    state = StateStub()
    artnet = DummyArtNet()
    manager = WebSocketManager(cast(Any, state), cast(Any, artnet), cast(Any, DummySongService()))
    ws = FakeWS()

    await manager.connect(cast(Any, ws))
    ws.sent.clear()

    await manager.handle_message(
        cast(Any, ws),
        json.dumps(
            {
                "type": "intent",
                "req_id": "req-3",
                "name": "llm.send_prompt",
                "payload": {"prompt": "hello world"},
            }
        ),
    )

    events = [msg for msg in ws.sent if msg.get("type") == "event"]
    assert len(events) >= 2
    assert events[0]["data"]["domain"] == "llm"
    assert events[-1]["data"]["done"] is True
