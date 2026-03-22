from typing import Any, Dict

from .sweep_helpers import (
    apply_dimmer_envelope,
    apply_leg_easing,
    circular_lerp_u16,
    clamp_byte,
    find_intensity_channel_key,
    max_dim_to_byte,
    parse_float,
)

SETTLE_SECONDS = 0.1


def handle(
    fixture,
    universe: bytearray,
    frame_index: int,
    start_frame: int,
    end_frame: int,
    fps: int,
    data: Dict[str, Any],
    render_state: Dict[str, Any],
) -> None:
    payload = data or {}
    subject_poi = str(payload.get("subject_POI") or "").strip()
    start_poi = str(payload.get("start_POI") or "").strip()
    if not subject_poi or not start_poi:
        return

    subject_pan, subject_tilt = fixture._resolve_poi_pan_tilt_u16(subject_poi)
    start_pan, start_tilt = fixture._resolve_poi_pan_tilt_u16(start_poi)
    if subject_pan is None or subject_tilt is None or start_pan is None or start_tilt is None:
        return

    mirrored_pan = fixture._clamp_u16((2 * int(subject_pan)) - int(start_pan))
    mirrored_tilt = fixture._clamp_u16((2 * int(subject_tilt)) - int(start_tilt))

    end_poi = str(payload.get("end_POI") or "").strip()
    if end_poi:
        end_pan, end_tilt = fixture._resolve_poi_pan_tilt_u16(end_poi)
        opposite_pan = fixture._clamp_u16(end_pan) if end_pan is not None else mirrored_pan
        opposite_tilt = fixture._clamp_u16(end_tilt) if end_tilt is not None else mirrored_tilt
    else:
        opposite_pan = mirrored_pan
        opposite_tilt = mirrored_tilt

    duration_seconds = parse_float(payload.get("duration"), 0.0)
    if duration_seconds <= 0.0:
        duration_seconds = max(1.0 / max(1, fps), (end_frame - start_frame) / float(max(1, fps)))

    preroll_frames = max(0, int((payload.get("__sweep_preroll_frames") or 0)))
    settle_frames = min(max(0, int(round(SETTLE_SECONDS * max(1, fps)))), preroll_frames)
    move_frames = max(0, preroll_frames - settle_frames)
    visible_start_frame = start_frame + preroll_frames
    visible_duration_frames = max(1, end_frame - visible_start_frame)
    motion_progress = (frame_index - visible_start_frame) / float(visible_duration_frames)
    motion_progress = max(0.0, min(1.0, motion_progress))

    easing_seconds = parse_float(payload.get("easing"), 0.0)
    arc_strength = parse_float(payload.get("arc_strength"), 0.015)
    dimmer_easing = parse_float(payload.get("dimmer_easing"), 0.0)
    visible_duration_seconds = max(1.0 / max(1, fps), visible_duration_frames / float(max(1, fps)))
    leg_duration_seconds = visible_duration_seconds * 0.5

    if "sweep_initial_pan_u16" not in render_state or "sweep_initial_tilt_u16" not in render_state:
        render_state["sweep_initial_pan_u16"] = int(fixture._read_axis_u16_from_universe(universe, "pan") or 0)
        render_state["sweep_initial_tilt_u16"] = int(fixture._read_axis_u16_from_universe(universe, "tilt") or 0)

    initial_pan = int(render_state.get("sweep_initial_pan_u16", 0))
    initial_tilt = int(render_state.get("sweep_initial_tilt_u16", 0))

    if frame_index < start_frame + move_frames:
        move_progress = (frame_index - start_frame) / float(max(1, move_frames))
        pan_u16 = fixture._clamp_u16(round(initial_pan + ((int(start_pan) - initial_pan) * move_progress)))
        tilt_u16 = fixture._clamp_u16(round(initial_tilt + ((int(start_tilt) - initial_tilt) * move_progress)))
        dim_factor = 0.0
    elif frame_index < visible_start_frame:
        pan_u16 = fixture._clamp_u16(start_pan)
        tilt_u16 = fixture._clamp_u16(start_tilt)
        dim_factor = 0.0
    elif motion_progress <= 0.5:
        leg_progress = apply_leg_easing(motion_progress * 2.0, easing_seconds, leg_duration_seconds, ease_in=False)
        pan_next, tilt_next = circular_lerp_u16(
            start_pan=start_pan,
            start_tilt=start_tilt,
            end_pan=subject_pan,
            end_tilt=subject_tilt,
            t=leg_progress,
            arc_strength=arc_strength,
        )
        pan_u16 = fixture._clamp_u16(pan_next)
        tilt_u16 = fixture._clamp_u16(tilt_next)
        dim_factor = apply_dimmer_envelope(motion_progress, dimmer_easing)
    else:
        leg_progress = apply_leg_easing((motion_progress - 0.5) * 2.0, easing_seconds, leg_duration_seconds, ease_in=True)
        pan_next, tilt_next = circular_lerp_u16(
            start_pan=subject_pan,
            start_tilt=subject_tilt,
            end_pan=opposite_pan,
            end_tilt=opposite_tilt,
            t=leg_progress,
            arc_strength=arc_strength,
        )
        pan_u16 = fixture._clamp_u16(pan_next)
        tilt_u16 = fixture._clamp_u16(tilt_next)
        dim_factor = apply_dimmer_envelope(motion_progress, dimmer_easing)

    if pan_u16 == subject_pan and tilt_u16 == subject_tilt:
        dim_factor = 1.0

    max_dim_byte = max_dim_to_byte(payload.get("max_dim", 1.0))
    intensity = clamp_byte(round(max_dim_byte * max(0.0, min(1.0, dim_factor))))

    fixture._write_axis_u16_to_universe(universe, "pan", pan_u16)
    fixture._write_axis_u16_to_universe(universe, "tilt", tilt_u16)

    intensity_key = find_intensity_channel_key(fixture)
    if intensity_key:
        fixture._write_channel(universe, intensity_key, intensity)

    if "shutter" in (fixture.channels or {}):
        fixture._write_channel(universe, "shutter", 255)
