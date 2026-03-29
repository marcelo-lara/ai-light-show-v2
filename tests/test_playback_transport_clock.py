import pytest

from store.state import StateManager
from store.state_manager.core import bootstrap as bootstrap_module
from store.state_manager.playback import transport as transport_module


@pytest.mark.asyncio
async def test_playback_timecode_uses_monotonic_anchor(monkeypatch, tmp_path):
    clock = {"now": 100.0}

    def fake_perf_counter() -> float:
        return clock["now"]

    monkeypatch.setattr(bootstrap_module, "perf_counter", fake_perf_counter)
    monkeypatch.setattr(transport_module, "perf_counter", fake_perf_counter)

    state_manager = StateManager(backend_path=tmp_path / "backend")
    state_manager.song_length_seconds = 90.0

    await state_manager.seek_timecode(12.345)
    await state_manager.set_playback_state(True)

    clock["now"] += 1.234
    live_timecode = await state_manager.get_timecode()
    assert abs(live_timecode - 13.579) < 0.01

    clock["now"] += 0.456
    await state_manager.advance_timecode(1 / 60)
    advanced_timecode = await state_manager.get_timecode()
    assert abs(advanced_timecode - 14.035) < 0.01

    await state_manager.set_playback_state(False)
    paused_timecode = await state_manager.get_timecode()
    assert abs(paused_timecode - 14.035) < 0.01