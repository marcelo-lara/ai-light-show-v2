from pathlib import Path
from types import SimpleNamespace

import pytest

from api.intents.fixture.actions.set_values import set_values
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

    songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = Path("/app/meta") if Path("/app/meta").exists() else backend_path / "meta"

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
