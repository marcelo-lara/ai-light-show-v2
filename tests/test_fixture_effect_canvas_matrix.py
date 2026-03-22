from types import SimpleNamespace

import pytest

from backend.models.cues import CueSheet
from tests.fixture_effect_matrix import EFFECT_START_S, FIXTURES_PATH, build_state_manager, case_id, cue_entries, effect_cases


@pytest.mark.asyncio
@pytest.mark.parametrize("case", effect_cases(), ids=case_id)
async def test_canvas_renders_every_declared_fixture_effect(case):
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    state_manager.current_song = SimpleNamespace(song_id="fixture_effect_canvas", meta=SimpleNamespace(bpm=120.0))
    if case.get("pois"):
        state_manager.poi_db.pois = case["pois"]

    state_manager.cue_sheet = CueSheet(song_filename="fixture_effect_canvas", entries=cue_entries(case))
    state_manager.song_length_seconds = EFFECT_START_S + case["duration"] + 1.0
    canvas = state_manager._render_cue_sheet_to_canvas()

    start_frame = int(EFFECT_START_S * canvas.fps)
    end_frame = min(canvas.total_frames - 1, int((EFFECT_START_S + case["duration"]) * canvas.fps))
    baseline_frame = bytes(canvas.frame_view(max(0, start_frame - 1)))

    assert any(bytes(canvas.frame_view(frame_index)) != baseline_frame for frame_index in range(start_frame, end_frame + 1))