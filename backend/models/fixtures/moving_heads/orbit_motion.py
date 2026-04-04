from typing import Any, Dict

from .orbit_helpers import orbit_writes_dimmer, spiral_orbit_position
from .sweep_helpers import find_intensity_channel_key
from .travel_helpers import EFFECT_SETTLE_SECONDS, limit_axis_step, max_axis_step_per_frame


def render_orbit_motion(
    fixture,
    universe: bytearray,
    frame_index: int,
    start_frame: int,
    end_frame: int,
    fps: int,
    data: Dict[str, Any],
    render_state: Dict[str, Any],
    *,
    outward: bool,
    state_prefix: str,
) -> None:
    if not (fixture._has_axis_16bit("pan") and fixture._has_axis_16bit("tilt")):
        return

    payload = data or {}
    subject_poi = str(payload.get("subject_POI") or "").strip()
    start_poi = str(payload.get("start_POI") or "").strip()
    if not subject_poi or not start_poi:
        return

    subject_pan_u16, subject_tilt_u16 = fixture._resolve_poi_pan_tilt_u16(subject_poi)
    start_pan_u16, start_tilt_u16 = fixture._resolve_poi_pan_tilt_u16(start_poi)
    if subject_pan_u16 is None or subject_tilt_u16 is None or start_pan_u16 is None or start_tilt_u16 is None:
        return

    intensity_key = find_intensity_channel_key(fixture)
    write_dimmer = orbit_writes_dimmer(payload)
    use_preroll = write_dimmer and bool(intensity_key)
    preroll_frames = max(0, int(payload.get("__orbit_preroll_frames") or 0)) if use_preroll else 0
    settle_frames = min(max(0, int(round(EFFECT_SETTLE_SECONDS * max(1, fps)))), preroll_frames)
    move_frames = max(0, preroll_frames - settle_frames)
    visible_start_frame = start_frame + preroll_frames
    preroll_pan_u16 = int(subject_pan_u16) if outward else int(start_pan_u16)
    preroll_tilt_u16 = int(subject_tilt_u16) if outward else int(start_tilt_u16)

    initial_pan_key = f"{state_prefix}_initial_pan_u16"
    initial_tilt_key = f"{state_prefix}_initial_tilt_u16"
    last_pan_key = f"{state_prefix}_last_pan_u16"
    last_tilt_key = f"{state_prefix}_last_tilt_u16"
    initial_intensity_key = f"{state_prefix}_initial_intensity"

    if initial_pan_key not in render_state or initial_tilt_key not in render_state:
        render_state[initial_pan_key] = int(fixture._read_axis_u16_from_universe(universe, "pan") or 0)
        render_state[initial_tilt_key] = int(fixture._read_axis_u16_from_universe(universe, "tilt") or 0)
    if last_pan_key not in render_state or last_tilt_key not in render_state:
        render_state[last_pan_key] = int(render_state.get(initial_pan_key, 0))
        render_state[last_tilt_key] = int(render_state.get(initial_tilt_key, 0))
    if write_dimmer and intensity_key and initial_intensity_key not in render_state:
        render_state[initial_intensity_key] = int(universe[fixture.absolute_channels[intensity_key] - 1])

    last_pan_u16 = int(render_state.get(last_pan_key, 0))
    last_tilt_u16 = int(render_state.get(last_tilt_key, 0))
    max_pan_step, max_tilt_step = max_axis_step_per_frame(fixture, fps)

    if frame_index < start_frame + move_frames:
        move_progress = (frame_index - start_frame) / float(max(1, move_frames))
        target_pan_u16 = round(int(render_state.get(initial_pan_key, 0)) + ((preroll_pan_u16 - int(render_state.get(initial_pan_key, 0))) * move_progress))
        target_tilt_u16 = round(int(render_state.get(initial_tilt_key, 0)) + ((preroll_tilt_u16 - int(render_state.get(initial_tilt_key, 0))) * move_progress))
        pan_value = fixture._clamp_u16(limit_axis_step(last_pan_u16, target_pan_u16, max_pan_step))
        tilt_value = fixture._clamp_u16(limit_axis_step(last_tilt_u16, target_tilt_u16, max_tilt_step))
        if write_dimmer and intensity_key:
            fixture._write_channel(universe, intensity_key, 0)
    elif frame_index < visible_start_frame:
        pan_value = fixture._clamp_u16(preroll_pan_u16)
        tilt_value = fixture._clamp_u16(preroll_tilt_u16)
        if write_dimmer and intensity_key:
            fixture._write_channel(universe, intensity_key, 0)
    else:
        duration_frames = max(1, end_frame - visible_start_frame)
        progress = max(0.0, min(1.0, (frame_index - visible_start_frame) / float(duration_frames)))
        orbit_progress = 1.0 - progress if outward else progress
        target_pan_u16, target_tilt_u16 = spiral_orbit_position(
            start_pan=int(start_pan_u16),
            start_tilt=int(start_tilt_u16),
            subject_pan=int(subject_pan_u16),
            subject_tilt=int(subject_tilt_u16),
            progress=orbit_progress,
            orbits=payload.get("orbits", 1.0),
            easing=payload.get("easing", "late_focus"),
        )
        pan_value = fixture._clamp_u16(limit_axis_step(last_pan_u16, target_pan_u16, max_pan_step))
        tilt_value = fixture._clamp_u16(limit_axis_step(last_tilt_u16, target_tilt_u16, max_tilt_step))
        if write_dimmer and intensity_key:
            fixture._write_channel(universe, intensity_key, int(render_state.get(initial_intensity_key, 0)))

    fixture._write_axis_u16_to_universe(universe, "pan", pan_value)
    fixture._write_axis_u16_to_universe(universe, "tilt", tilt_value)
    render_state[last_pan_key] = int(pan_value)
    render_state[last_tilt_key] = int(tilt_value)
