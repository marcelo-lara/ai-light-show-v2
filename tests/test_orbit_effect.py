import math
from types import SimpleNamespace

import pytest

from backend.models.cues import CueSheet
from backend.models.fixtures.moving_heads.poi_geometry import estimate_circle_pan_tilt
from backend.models.fixtures.moving_heads.orbit_helpers import spiral_orbit_position
from tests.fixture_effect_matrix import EFFECT_START_S, FIXTURES_PATH, POIS, build_state_manager

SETTLE_FRAMES = 6


async def _render_mover_effect(effect: str, data: dict, *, fixture_id: str = "head_el150", pois=None, duration: float = 1.0):
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    state_manager.current_song = SimpleNamespace(song_id=f"{effect}_effect", meta=SimpleNamespace(bpm=120.0))
    state_manager.poi_db.pois = POIS if pois is None else pois
    fixture = next(item for item in state_manager.fixtures if item.id == fixture_id)
    payload = dict(data)
    initial_pan = payload.pop("__initial_pan", None)
    initial_tilt = payload.pop("__initial_tilt", None)
    initial_dim = payload.pop("__initial_dim", None)
    setup_full = bool(payload.pop("__setup_full", False))
    if initial_pan is not None and initial_tilt is not None:
        fixture.current_values["pan"] = int(initial_pan)
        fixture.current_values["tilt"] = int(initial_tilt)
        fixture._write_axis_u16_to_universe(state_manager.editor_universe, "pan", int(initial_pan))
        fixture._write_axis_u16_to_universe(state_manager.editor_universe, "tilt", int(initial_tilt))
    if initial_dim is not None and "dim" in fixture.absolute_channels:
        state_manager.editor_universe[fixture.absolute_channels["dim"] - 1] = int(initial_dim)
    entries = []
    if setup_full:
        entries.append({"time": 0.0, "fixture_id": fixture_id, "effect": "full", "duration": 0.25, "data": {}})
    entries.append({"time": EFFECT_START_S, "fixture_id": fixture_id, "effect": effect, "duration": duration, "data": payload})
    state_manager.cue_sheet = CueSheet(
        song_filename=f"{effect}_effect",
        entries=entries,
    )
    state_manager.song_length_seconds = EFFECT_START_S + duration + 0.5
    canvas = state_manager._render_cue_sheet_to_canvas()
    return canvas, fixture, int(EFFECT_START_S * canvas.fps)


def _u16(frame, fixture, axis: str) -> int:
    msb_index = fixture.absolute_channels[f"{axis}_msb"] - 1
    lsb_index = fixture.absolute_channels[f"{axis}_lsb"] - 1
    return (frame[msb_index] << 8) | frame[lsb_index]


def _u8(frame, fixture, channel: str) -> int:
    return int(frame[fixture.absolute_channels[channel] - 1])


@pytest.mark.asyncio
async def test_orbit_orbits_around_subject_then_lands_on_it():
    canvas, fixture, start_frame = await _render_mover_effect("orbit", {"subject_POI": "subject", "start_POI": "start", "orbits": 1.0, "easing": "linear"})
    start = canvas.frame_view(start_frame)
    quarter = canvas.frame_view(start_frame + 15)
    end = canvas.frame_view(start_frame + 60)
    quarter_linear_pan = round(6000 + ((30000 - 6000) * 0.25))
    quarter_linear_tilt = round(10000 + ((36000 - 10000) * 0.25))

    assert _u16(start, fixture, "pan") == 6000
    assert _u16(start, fixture, "tilt") == 10000
    assert _u16(end, fixture, "pan") == 30000
    assert _u16(end, fixture, "tilt") == 36000
    assert _u16(quarter, fixture, "pan") != quarter_linear_pan
    assert _u16(quarter, fixture, "tilt") != quarter_linear_tilt


def test_orbit_easing_controls_how_late_the_spiral_tightens():
    def radius(pan: int, tilt: int) -> float:
        return math.hypot(pan - 30000, tilt - 36000)

    late_pan, late_tilt = spiral_orbit_position(
        start_pan=6000,
        start_tilt=10000,
        subject_pan=30000,
        subject_tilt=36000,
        progress=0.5,
        orbits=1.0,
        easing="late_focus",
    )
    linear_pan, linear_tilt = spiral_orbit_position(
        start_pan=6000,
        start_tilt=10000,
        subject_pan=30000,
        subject_tilt=36000,
        progress=0.5,
        orbits=1.0,
        easing="linear",
    )
    early_pan, early_tilt = spiral_orbit_position(
        start_pan=6000,
        start_tilt=10000,
        subject_pan=30000,
        subject_tilt=36000,
        progress=0.5,
        orbits=1.0,
        easing="early_focus",
    )

    assert radius(late_pan, late_tilt) > radius(linear_pan, linear_tilt) > radius(early_pan, early_tilt)


@pytest.mark.asyncio
async def test_orbit_prerolls_dark_to_start_poi_before_visible_motion():
    canvas, fixture, start_frame = await _render_mover_effect(
        "orbit",
        {
            "subject_POI": "subject",
            "start_POI": "start",
            "orbits": 1.0,
            "easing": "late_focus",
            "__initial_pan": 0,
            "__initial_tilt": 0,
            "__setup_full": True,
        },
        fixture_id="mini_beam_prism_l",
    )

    for frame_index in range(start_frame - SETTLE_FRAMES, start_frame):
        frame = canvas.frame_view(frame_index)
        assert _u16(frame, fixture, "pan") == 4000
        assert _u16(frame, fixture, "tilt") == 8000
        assert _u8(frame, fixture, "dim") == 0

    visible_start = canvas.frame_view(start_frame)
    assert _u8(visible_start, fixture, "dim") == 255


@pytest.mark.asyncio
async def test_orbit_respects_max_travel_per_frame_for_physical_profile():
    canvas, fixture, start_frame = await _render_mover_effect(
        "orbit",
        {
            "subject_POI": "subject",
            "start_POI": "start",
            "orbits": 2.0,
            "easing": "late_focus",
            "__initial_pan": 0,
            "__initial_tilt": 0,
        },
        fixture_id="mini_beam_prism_l",
    )

    max_pan_step = math.ceil(65535.0 / (2.0 * canvas.fps))
    max_tilt_step = math.ceil(65535.0 / (0.9 * canvas.fps))
    previous = canvas.frame_view(start_frame)
    for frame_index in range(start_frame + 1, start_frame + 61):
        current = canvas.frame_view(frame_index)
        assert abs(_u16(current, fixture, "pan") - _u16(previous, fixture, "pan")) <= max_pan_step
        assert abs(_u16(current, fixture, "tilt") - _u16(previous, fixture, "tilt")) <= max_tilt_step
        previous = current


@pytest.mark.asyncio
async def test_orbit_preview_prerolls_from_last_position():
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    state_manager.current_song = SimpleNamespace(song_id="orbit_preview", meta=SimpleNamespace(bpm=120.0))
    state_manager.poi_db.pois = POIS
    fixture = next(item for item in state_manager.fixtures if item.id == "mini_beam_prism_l")
    fixture.current_values["pan"] = 0
    fixture.current_values["tilt"] = 0
    fixture._write_axis_u16_to_universe(state_manager.editor_universe, "pan", 0)
    fixture._write_axis_u16_to_universe(state_manager.editor_universe, "tilt", 0)
    state_manager.editor_universe[fixture.absolute_channels["dim"] - 1] = 180

    started = await state_manager.start_preview_effect(
        fixture_id="mini_beam_prism_l",
        effect="orbit",
        duration=1.0,
        data={"subject_POI": "subject", "start_POI": "start", "orbits": 1.0, "easing": "late_focus"},
        request_id="orbit-preview-preroll",
    )

    assert started["ok"] is True
    assert state_manager.preview_canvas is not None
    assert state_manager.preview_canvas.total_frames > 61
    visible_start_frame = state_manager.preview_canvas.total_frames - 61

    for frame_index in range(visible_start_frame - SETTLE_FRAMES, visible_start_frame):
        frame = state_manager.preview_canvas.frame_view(frame_index)
        assert _u16(frame, fixture, "pan") == 4000
        assert _u16(frame, fixture, "tilt") == 8000
        assert _u8(frame, fixture, "dim") == 0

    visible_start = state_manager.preview_canvas.frame_view(visible_start_frame)
    subject_end = state_manager.preview_canvas.frame_view(state_manager.preview_canvas.total_frames - 1)
    assert _u8(visible_start, fixture, "dim") == 180
    assert math.hypot(_u16(subject_end, fixture, "pan") - 30000, _u16(subject_end, fixture, "tilt") - 36000) < math.hypot(4000 - 30000, 8000 - 36000)

    await state_manager.wait_for_preview_end(started["requestId"])


@pytest.mark.asyncio
async def test_orbit_can_skip_dimmer_writes_and_preroll():
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    state_manager.current_song = SimpleNamespace(song_id="orbit_preview_no_dimmer", meta=SimpleNamespace(bpm=120.0))
    state_manager.poi_db.pois = POIS
    fixture = next(item for item in state_manager.fixtures if item.id == "mini_beam_prism_l")
    fixture.current_values["pan"] = 0
    fixture.current_values["tilt"] = 0
    fixture._write_axis_u16_to_universe(state_manager.editor_universe, "pan", 0)
    fixture._write_axis_u16_to_universe(state_manager.editor_universe, "tilt", 0)
    state_manager.editor_universe[fixture.absolute_channels["dim"] - 1] = 180

    started = await state_manager.start_preview_effect(
        fixture_id="mini_beam_prism_l",
        effect="orbit",
        duration=1.0,
        data={"subject_POI": "subject", "start_POI": "start", "orbits": 1.0, "easing": "late_focus", "write_dimmer": False},
        request_id="orbit-preview-no-dimmer",
    )

    assert started["ok"] is True
    assert state_manager.preview_canvas is not None
    assert state_manager.preview_canvas.total_frames == 61
    assert all(_u8(state_manager.preview_canvas.frame_view(index), fixture, "dim") == 180 for index in range(state_manager.preview_canvas.total_frames))
    await state_manager.wait_for_preview_end(started["requestId"])


@pytest.mark.asyncio
async def test_orbit_out_starts_on_subject_and_spirals_back_to_start():
    canvas, fixture, start_frame = await _render_mover_effect(
        "orbit_out",
        {"subject_POI": "subject", "start_POI": "start", "orbits": 1.0, "easing": "linear"},
        duration=2.0,
    )

    start = canvas.frame_view(start_frame)
    middle = canvas.frame_view(start_frame + 60)
    end = canvas.frame_view(start_frame + 120)
    assert _u16(start, fixture, "pan") == 30000
    assert _u16(start, fixture, "tilt") == 36000
    assert math.hypot(_u16(end, fixture, "pan") - 6000, _u16(end, fixture, "tilt") - 10000) < math.hypot(_u16(middle, fixture, "pan") - 6000, _u16(middle, fixture, "tilt") - 10000)
    assert math.hypot(_u16(end, fixture, "pan") - 6000, _u16(end, fixture, "tilt") - 10000) < math.hypot(30000 - 6000, 36000 - 10000)


@pytest.mark.asyncio
async def test_circle_uses_reference_geometry_around_target_location():
    circle_pois = [
        {"id": "target", "location": {"x": 0.5, "y": 0.5, "z": 0.0}, "fixtures": {}},
        {"id": "ref_0_0_0", "location": {"x": 0.0, "y": 0.0, "z": 0.0}, "fixtures": {"head_el150": {"pan": 10000, "tilt": 10000}}},
        {"id": "ref_1_0_0", "location": {"x": 1.0, "y": 0.0, "z": 0.0}, "fixtures": {"head_el150": {"pan": 50000, "tilt": 12000}}},
        {"id": "ref_1_1_0", "location": {"x": 1.0, "y": 1.0, "z": 0.0}, "fixtures": {"head_el150": {"pan": 52000, "tilt": 50000}}},
        {"id": "ref_0_1_0", "location": {"x": 0.0, "y": 1.0, "z": 0.0}, "fixtures": {"head_el150": {"pan": 12000, "tilt": 52000}}},
    ]
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    state_manager.current_song = SimpleNamespace(song_id="circle_preview", meta=SimpleNamespace(bpm=120.0))
    state_manager.poi_db.pois = circle_pois
    fixture = next(item for item in state_manager.fixtures if item.id == "head_el150")
    start_pan, start_tilt = estimate_circle_pan_tilt(fixture, {"target_poi": "target", "radius": 0.25, "orbits": 1.0}, 0.0)
    fixture.current_values["pan"] = int(start_pan)
    fixture.current_values["tilt"] = int(start_tilt)
    fixture._write_axis_u16_to_universe(state_manager.editor_universe, "pan", int(start_pan))
    fixture._write_axis_u16_to_universe(state_manager.editor_universe, "tilt", int(start_tilt))

    started = await state_manager.start_preview_effect(
        fixture_id="head_el150",
        effect="circle",
        duration=2.0,
        data={"target_poi": "target", "radius": 0.25, "orbits": 1.0},
        request_id="circle-preview-geometry",
    )
    assert started["ok"] is True
    assert state_manager.preview_canvas is not None

    start = state_manager.preview_canvas.frame_view(0)
    quarter = state_manager.preview_canvas.frame_view(30)
    half = state_manager.preview_canvas.frame_view(60)
    end = state_manager.preview_canvas.frame_view(120)

    start_position = (_u16(start, fixture, "pan"), _u16(start, fixture, "tilt"))
    quarter_position = (_u16(quarter, fixture, "pan"), _u16(quarter, fixture, "tilt"))
    half_position = (_u16(half, fixture, "pan"), _u16(half, fixture, "tilt"))
    end_position = (_u16(end, fixture, "pan"), _u16(end, fixture, "tilt"))

    assert start_position == (int(start_pan), int(start_tilt))
    assert start_position != quarter_position
    assert quarter_position != half_position
    assert math.hypot(end_position[0] - start_position[0], end_position[1] - start_position[1]) < math.hypot(half_position[0] - start_position[0], half_position[1] - start_position[1])
    await state_manager.wait_for_preview_end(started["requestId"])