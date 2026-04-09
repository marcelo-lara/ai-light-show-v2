import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.models.cues import CueSheet
from backend.models.fixtures.moving_heads.sweep_helpers import apply_leg_easing
from tests.fixture_effect_matrix import EFFECT_START_S, FIXTURES_PATH, POIS, build_state_manager

POIS_PATH = Path(__file__).resolve().parents[1] / "backend" / "fixtures" / "pois.json"
with open(POIS_PATH, "r", encoding="utf-8") as handle:
    REAL_POIS = json.load(handle)

SETTLE_FRAMES = 6


async def _render_sweep(data: dict, *, fixture_id: str = "head_el150", pois: list[dict] = POIS):
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    state_manager.current_song = SimpleNamespace(song_id="sweep_effect", meta=SimpleNamespace(bpm=120.0))
    state_manager.poi_db.pois = pois
    fixture = next(item for item in state_manager.fixtures if item.id == fixture_id)
    initial_pan = data.pop("__initial_pan", None)
    initial_tilt = data.pop("__initial_tilt", None)
    if initial_pan is not None and initial_tilt is not None:
        fixture.current_values["pan"] = int(initial_pan)
        fixture.current_values["tilt"] = int(initial_tilt)
    effect_duration = float(data.get("duration", 0.5) or 0.5)
    state_manager.cue_sheet = CueSheet(
        song_filename="sweep_effect",
        entries=[{"time": EFFECT_START_S, "fixture_id": fixture_id, "effect": "sweep", "duration": effect_duration, "data": data}],
    )
    state_manager.song_length_seconds = EFFECT_START_S + effect_duration + 1.0
    canvas = state_manager._render_cue_sheet_to_canvas()
    return canvas, fixture, int(EFFECT_START_S * canvas.fps)


def _u8(frame, fixture, channel: str) -> int:
    return frame[fixture.absolute_channels[channel] - 1]


def _u16(frame, fixture, axis: str) -> int:
    msb_index = fixture.absolute_channels[f"{axis}_msb"] - 1
    lsb_index = fixture.absolute_channels[f"{axis}_lsb"] - 1
    return (frame[msb_index] << 8) | frame[lsb_index]


def _poi_target(poi_id: str, fixture_id: str) -> tuple[int, int]:
    for poi in REAL_POIS:
        if str(poi.get("id") or "").strip().lower() != poi_id:
            continue
        fixtures = poi.get("fixtures") or {}
        values = fixtures.get(fixture_id) or {}
        return int(values.get("pan", 0)), int(values.get("tilt", 0))
    raise AssertionError(f"POI '{poi_id}' missing fixture '{fixture_id}'")


@pytest.mark.asyncio
async def test_sweep_dimmer_easing_delays_fade_and_hits_peak_at_subject():
    base_data = {"subject_POI": "subject", "start_POI": "start", "end_POI": "end", "duration": 1.0, "easing": 0.5, "max_dim": 1.0}
    early_canvas, fixture, start_frame = await _render_sweep(dict(base_data, dimmer_easing=0.0))
    late_canvas, _, _ = await _render_sweep(dict(base_data, dimmer_easing=0.9))
    subject_frame = start_frame + 30
    approach_frame = start_frame + 8

    assert _u8(early_canvas.frame_view(subject_frame), fixture, "dim") == 255
    assert _u8(late_canvas.frame_view(subject_frame), fixture, "dim") == 255
    assert _u16(early_canvas.frame_view(subject_frame), fixture, "pan") == 30000
    assert _u16(early_canvas.frame_view(subject_frame), fixture, "tilt") == 36000
    assert _u8(early_canvas.frame_view(approach_frame), fixture, "dim") > _u8(late_canvas.frame_view(approach_frame), fixture, "dim")
    assert _u8(late_canvas.frame_view(approach_frame), fixture, "dim") == 0


def test_sweep_uses_cubic_easing_per_leg():
    approach_progress = apply_leg_easing(4.0 / 15.0, 0.5, 0.5, ease_in=False)
    depart_progress = apply_leg_easing(4.0 / 15.0, 0.5, 0.5, ease_in=True)

    assert approach_progress > (4.0 / 15.0)
    assert depart_progress < (4.0 / 15.0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fixture_id",),
    [
        ("mini_beam_prism_l",),
        ("mini_beam_prism_r",),
        ("head_el150",),
    ],
)
async def test_sweep_moves_toward_real_table_poi_from_piano_for_all_moving_heads(
    fixture_id: str,
):
    initial_pan, initial_tilt = _poi_target("piano", fixture_id)
    expected_pan, expected_tilt = _poi_target("table", fixture_id)
    canvas, fixture, start_frame = await _render_sweep(
        {
            "subject_POI": "table",
            "start_POI": "piano",
            "duration": 0.5,
            "easing": 0.5,
            "dimmer_easing": 0.0,
            "max_dim": 1.0,
            "__initial_pan": initial_pan,
            "__initial_tilt": initial_tilt,
        },
        fixture_id=fixture_id,
        pois=REAL_POIS,
    )
    subject_frame = start_frame + 15
    baseline_frame = bytes(canvas.frame_view(start_frame - 1))
    subject = canvas.frame_view(subject_frame)
    start_distance = math.hypot(initial_pan - expected_pan, initial_tilt - expected_tilt)
    subject_distance = math.hypot(_u16(subject, fixture, "pan") - expected_pan, _u16(subject, fixture, "tilt") - expected_tilt)

    assert any(bytes(canvas.frame_view(index)) != baseline_frame for index in range(start_frame, start_frame + 31))
    assert subject_distance < start_distance
    assert _u8(subject, fixture, "dim") > 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fixture_id",),
    [
        ("mini_beam_prism_l",),
        ("mini_beam_prism_r",),
        ("head_el150",),
    ],
)
async def test_sweep_holds_real_start_poi_before_visible_start(fixture_id: str):
    expected_pan, expected_tilt = _poi_target("piano", fixture_id)
    canvas, fixture, start_frame = await _render_sweep(
        {
            "subject_POI": "table",
            "start_POI": "piano",
            "duration": 0.5,
            "easing": 0.5,
            "dimmer_easing": 0.0,
            "max_dim": 1.0,
            "__initial_pan": expected_pan,
            "__initial_tilt": expected_tilt,
        },
        fixture_id=fixture_id,
        pois=REAL_POIS,
    )

    for frame_index in range(start_frame - SETTLE_FRAMES, start_frame):
        frame = canvas.frame_view(frame_index)
        assert _u16(frame, fixture, "pan") == expected_pan
        assert _u16(frame, fixture, "tilt") == expected_tilt
        assert _u8(frame, fixture, "dim") == 0


@pytest.mark.asyncio
async def test_sweep_preview_prerolls_to_start_poi_from_last_position():
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    state_manager.current_song = SimpleNamespace(song_id="sweep_preview", meta=SimpleNamespace(bpm=120.0))
    state_manager.poi_db.pois = REAL_POIS
    fixture = next(item for item in state_manager.fixtures if item.id == "mini_beam_prism_l")
    fixture.current_values["pan"] = 0
    fixture.current_values["tilt"] = 0
    fixture._write_axis_u16_to_universe(state_manager.editor_universe, "pan", 0)
    fixture._write_axis_u16_to_universe(state_manager.editor_universe, "tilt", 0)

    started = await state_manager.start_preview_effect(
        fixture_id="mini_beam_prism_l",
        effect="sweep",
        duration=0.5,
        data={"subject_POI": "table", "start_POI": "piano", "easing": 0.5, "dimmer_easing": 0.0, "max_dim": 1.0},
        request_id="sweep-preview-preroll",
    )

    assert started["ok"] is True
    assert state_manager.preview_canvas is not None
    assert state_manager.preview_canvas.total_frames > 31
    visible_start_frame = state_manager.preview_canvas.total_frames - 31
    dump_path = POIS_PATH.resolve().parents[1] / "cues" / "preview.mini_beam_prism_l.sweep.sweep-preview-preroll.dmx.log"
    assert dump_path.exists()
    assert dump_path.stat().st_size > 0
    piano_pan, piano_tilt = _poi_target("piano", "mini_beam_prism_l")
    table_pan, table_tilt = _poi_target("table", "mini_beam_prism_l")

    for frame_index in range(visible_start_frame - SETTLE_FRAMES, visible_start_frame):
        frame = state_manager.preview_canvas.frame_view(frame_index)
        assert _u16(frame, fixture, "pan") == piano_pan
        assert _u16(frame, fixture, "tilt") == piano_tilt
        assert _u8(frame, fixture, "dim") == 0

    subject = state_manager.preview_canvas.frame_view(visible_start_frame + 15)
    assert math.hypot(_u16(subject, fixture, "pan") - table_pan, _u16(subject, fixture, "tilt") - table_tilt) < math.hypot(piano_pan - table_pan, piano_tilt - table_tilt)
    assert _u8(subject, fixture, "dim") > 0

    await state_manager.wait_for_preview_end(started["requestId"])
    dump_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_sweep_respects_max_travel_per_frame_for_physical_profile():
    canvas, fixture, start_frame = await _render_sweep(
        {
            "subject_POI": "subject",
            "start_POI": "start",
            "end_POI": "end",
            "duration": 0.5,
            "easing": 0.5,
            "dimmer_easing": 0.0,
            "max_dim": 1.0,
            "__initial_pan": 0,
            "__initial_tilt": 0,
        },
        fixture_id="mini_beam_prism_l",
    )
    max_pan_step = math.ceil(65535.0 / (2.0 * canvas.fps))
    max_tilt_step = math.ceil(65535.0 / (0.9 * canvas.fps))

    previous = canvas.frame_view(max(0, start_frame - 1))
    for frame_index in range(start_frame, min(canvas.total_frames, start_frame + 31)):
        current = canvas.frame_view(frame_index)
        assert abs(_u16(current, fixture, "pan") - _u16(previous, fixture, "pan")) <= max_pan_step
        assert abs(_u16(current, fixture, "tilt") - _u16(previous, fixture, "tilt")) <= max_tilt_step
        previous = current