from types import SimpleNamespace

import pytest

from backend.models.cues import CueSheet
from tests.fixture_effect_matrix import FIXTURES_PATH, build_state_manager


def _u8(frame: bytearray | bytes, fixture, channel_name: str) -> int:
    return int(frame[fixture.absolute_channels[channel_name] - 1])


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture_id", ["mini_beam_prism_l", "head_el150"])
async def test_strobe_uses_dimmer_only_and_ends_black(fixture_id: str):
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    state_manager.current_song = SimpleNamespace(song_id="strobe_terminal_state", meta=SimpleNamespace(bpm=120.0))
    state_manager.cue_sheet = CueSheet(
        song_filename="strobe_terminal_state",
        entries=[
            {"time": 0.0, "fixture_id": fixture_id, "effect": "full", "duration": 0.25, "data": {}},
            {"time": 1.0, "fixture_id": fixture_id, "effect": "strobe", "duration": 0.5, "data": {"rate": 12.0}},
        ],
    )
    state_manager.song_length_seconds = 2.0

    canvas = state_manager._render_cue_sheet_to_canvas()
    fixture = next(item for item in state_manager.fixtures if item.id == fixture_id)
    start_frame = int(1.0 * canvas.fps)
    end_frame = min(canvas.total_frames - 1, int(1.5 * canvas.fps))
    after_end_frame = min(canvas.total_frames - 1, end_frame + 1)
    modulation_key = "strobe" if "strobe" in fixture.channels else "shutter" if "shutter" in fixture.channels else None
    baseline_frame = canvas.frame_view(max(0, start_frame - 1))
    active_frames = [canvas.frame_view(frame_index) for frame_index in range(start_frame, end_frame)]

    assert _u8(baseline_frame, fixture, "dim") == 255
    assert any(_u8(frame, fixture, "dim") == 255 for frame in active_frames)
    assert any(_u8(frame, fixture, "dim") == 0 for frame in active_frames)
    assert _u8(canvas.frame_view(end_frame), fixture, "dim") == 0
    assert _u8(canvas.frame_view(after_end_frame), fixture, "dim") == 0
    if modulation_key is not None:
        baseline_modulation = _u8(baseline_frame, fixture, modulation_key)
        assert all(_u8(frame, fixture, modulation_key) == baseline_modulation for frame in active_frames)
        assert _u8(canvas.frame_view(end_frame), fixture, modulation_key) == baseline_modulation
        assert _u8(canvas.frame_view(after_end_frame), fixture, modulation_key) == baseline_modulation