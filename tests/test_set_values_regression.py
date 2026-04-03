from pathlib import Path
from types import SimpleNamespace

import pytest

from api.intents.fixture.actions.set_values import set_values
from models.song import resolve_meta_root, resolve_songs_root
from store.state import StateManager


class ArtNetStub:
    def __init__(self):
        self.calls: list[tuple[int, int]] = []

    async def set_channel(self, channel: int, value: int):
        self.calls.append((channel, value))


@pytest.mark.asyncio
async def test_set_values_u8_u16_and_enum_paths():
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"

    songs_path = resolve_songs_root(backend_path)
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = resolve_meta_root(backend_path)

    sm = StateManager(backend_path, songs_path, cues_path, meta_path)
    await sm.load_fixtures(backend_path / "fixtures" / "fixtures.json")

    fixture = next(fx for fx in sm.fixtures if fx.id == "mini_beam_prism_l")
    artnet = ArtNetStub()
    manager = SimpleNamespace(state_manager=sm, artnet_service=artnet)

    # u8 path
    changed = await set_values(manager, {
        "fixture_id": fixture.id,
        "values": {"dim": 123},
    })
    assert changed is True
    assert (fixture.absolute_channels["dim"], 123) in artnet.calls
    output = await sm.get_output_universe()
    assert output[fixture.absolute_channels["dim"] - 1] == 123

    # u16 path
    artnet.calls.clear()
    changed = await set_values(manager, {
        "fixture_id": fixture.id,
        "values": {"pan": 4660},  # 0x1234
    })
    assert changed is True
    assert (fixture.absolute_channels["pan_msb"], 0x12) in artnet.calls
    assert (fixture.absolute_channels["pan_lsb"], 0x34) in artnet.calls
    output = await sm.get_output_universe()
    assert output[fixture.absolute_channels["pan_msb"] - 1] == 0x12
    assert output[fixture.absolute_channels["pan_lsb"] - 1] == 0x34

    # enum path: backend expects label and resolves to DMX value
    artnet.calls.clear()
    changed = await set_values(manager, {
        "fixture_id": fixture.id,
        "values": {"color": "Red"},
    })
    assert changed is True
    assert (fixture.absolute_channels["color"], 15) in artnet.calls
    output = await sm.get_output_universe()
    assert output[fixture.absolute_channels["color"] - 1] == 15


@pytest.mark.asyncio
async def test_set_values_accepts_rgb_hex_and_mapped_name_for_parcan_rgb():
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"

    songs_path = resolve_songs_root(backend_path)
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = resolve_meta_root(backend_path)

    sm = StateManager(backend_path, songs_path, cues_path, meta_path)
    await sm.load_fixtures(backend_path / "fixtures" / "fixtures.json")

    fixture = next(fx for fx in sm.fixtures if fx.id == "parcan_l")
    artnet = ArtNetStub()
    manager = SimpleNamespace(state_manager=sm, artnet_service=artnet)

    changed = await set_values(manager, {
        "fixture_id": fixture.id,
        "values": {"rgb": "#578feb"},
    })

    assert changed is True
    assert (fixture.absolute_channels["red"], 0x57) in artnet.calls
    assert (fixture.absolute_channels["green"], 0x8F) in artnet.calls
    assert (fixture.absolute_channels["blue"], 0xEB) in artnet.calls
    assert fixture.current_values.get("rgb") == "#578FEB"

    output = await sm.get_output_universe()
    assert output[fixture.absolute_channels["red"] - 1] == 0x57
    assert output[fixture.absolute_channels["green"] - 1] == 0x8F
    assert output[fixture.absolute_channels["blue"] - 1] == 0xEB

    artnet.calls.clear()
    changed = await set_values(manager, {
        "fixture_id": fixture.id,
        "values": {"rgb": "red"},
    })

    assert changed is True
    assert (fixture.absolute_channels["red"], 255) in artnet.calls
    assert (fixture.absolute_channels["green"], 0) in artnet.calls
    assert (fixture.absolute_channels["blue"], 0) in artnet.calls

    output = await sm.get_output_universe()
    assert output[fixture.absolute_channels["red"] - 1] == 255
    assert output[fixture.absolute_channels["green"] - 1] == 0
    assert output[fixture.absolute_channels["blue"] - 1] == 0


@pytest.mark.asyncio
async def test_set_values_rejects_direct_rgb_channels_for_parcan_rgb():
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"

    songs_path = resolve_songs_root(backend_path)
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = resolve_meta_root(backend_path)

    sm = StateManager(backend_path, songs_path, cues_path, meta_path)
    await sm.load_fixtures(backend_path / "fixtures" / "fixtures.json")

    fixture = next(fx for fx in sm.fixtures if fx.id == "parcan_l")
    artnet = ArtNetStub()
    manager = SimpleNamespace(state_manager=sm, artnet_service=artnet)

    changed = await set_values(manager, {
        "fixture_id": fixture.id,
        "values": {"red": 255, "green": 64, "blue": 10},
    })

    assert changed is False
    assert artnet.calls == []

    output = await sm.get_output_universe()
    assert output[fixture.absolute_channels["red"] - 1] == 0
    assert output[fixture.absolute_channels["green"] - 1] == 0
    assert output[fixture.absolute_channels["blue"] - 1] == 0
