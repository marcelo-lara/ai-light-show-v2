from typing import Any, Dict

from .sweep_helpers import (
    apply_time_easing,
    circular_lerp_u16,
    clamp_byte,
    find_intensity_channel_key,
    invert_easing_for_dimmer,
    max_dim_to_byte,
    parse_float,
    subject_closeness_factor,
)


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

    total_frames = max(1, int(round(duration_seconds * max(1, fps))))
    progress = (frame_index - start_frame) / float(total_frames)
    progress = max(0.0, min(1.0, progress))

    easing_seconds = parse_float(payload.get("easing"), 0.0)
    arc_strength = parse_float(payload.get("arc_strength"), 0.015)
    subject_close_ratio = parse_float(payload.get("subject_close_ratio"), 0.1)
    eased_progress = apply_time_easing(progress, easing_seconds, duration_seconds)
    dimmer_easing_seconds = invert_easing_for_dimmer(easing_seconds, duration_seconds)
    dimmer_progress = apply_time_easing(progress, dimmer_easing_seconds, duration_seconds)

    if eased_progress <= 0.5:
        leg_progress = eased_progress * 2.0
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
    else:
        leg_progress = (eased_progress - 0.5) * 2.0
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

    if dimmer_progress <= 0.5:
        dim_factor = dimmer_progress * 2.0
    else:
        dim_factor = 1.0 - ((dimmer_progress - 0.5) * 2.0)

    closeness = subject_closeness_factor(
        current_pan=pan_u16,
        current_tilt=tilt_u16,
        subject_pan=subject_pan,
        subject_tilt=subject_tilt,
        approach_start_pan=start_pan,
        approach_start_tilt=start_tilt,
        close_ratio=subject_close_ratio,
    )
    dim_factor = dim_factor * closeness

    max_dim_byte = max_dim_to_byte(payload.get("max_dim", 1.0))
    intensity = clamp_byte(round(max_dim_byte * max(0.0, min(1.0, dim_factor))))

    fixture._write_axis_u16_to_universe(universe, "pan", pan_u16)
    fixture._write_axis_u16_to_universe(universe, "tilt", tilt_u16)

    intensity_key = find_intensity_channel_key(fixture)
    if intensity_key:
        fixture._write_channel(universe, intensity_key, intensity)

    if "shutter" in (fixture.channels or {}):
        fixture._write_channel(universe, "shutter", 255)
