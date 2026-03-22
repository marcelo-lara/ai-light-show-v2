from types import SimpleNamespace

import pytest

from tests.fixture_effect_matrix import FIXTURES_PATH, apply_preview_setup, build_state_manager, case_id, effect_cases


@pytest.mark.asyncio
@pytest.mark.parametrize("case", effect_cases(), ids=case_id)
async def test_preview_supports_every_declared_fixture_effect(case):
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    state_manager.current_song = SimpleNamespace(song_id="fixture_effect_preview", meta=SimpleNamespace(bpm=120.0))
    apply_preview_setup(state_manager, case)

    started = await state_manager.start_preview_effect(
        fixture_id=case["fixture_id"],
        effect=case["effect"],
        duration=case["duration"],
        data=case["data"],
        request_id=case_id(case),
    )

    assert started["ok"] is True
    assert state_manager.preview_canvas is not None
    base_frame = bytes(state_manager.editor_universe)
    assert any(
        bytes(state_manager.preview_canvas.frame_view(frame_index)) != base_frame
        for frame_index in range(state_manager.preview_canvas.total_frames)
    )

    await state_manager.wait_for_preview_end(started["requestId"])
    assert state_manager.preview_active is False