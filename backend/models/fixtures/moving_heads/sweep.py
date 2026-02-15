import math
from typing import Any, Dict, Optional, Tuple


def _clamp_byte(value: Any) -> int:
    try:
        iv = int(value)
    except Exception:
        return 0
    return max(0, min(255, iv))


def _parse_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _find_intensity_channel_key(fixture) -> Optional[str]:
    for k in ("dim", "dimmer", "intensity"):
        if k in (fixture.channels or {}):
            return k
    return None


def _lerp_u16(a: int, b: int, t: float) -> int:
    t = max(0.0, min(1.0, float(t)))
    return int(round(a + (b - a) * t))


def _circular_lerp_u16(
    *,
    start_pan: int,
    start_tilt: int,
    end_pan: int,
    end_tilt: int,
    t: float,
    arc_strength: float,
) -> Tuple[int, int]:
    progress = max(0.0, min(1.0, float(t)))

    pan_linear = float(_lerp_u16(start_pan, end_pan, progress))
    tilt_linear = float(_lerp_u16(start_tilt, end_tilt, progress))

    delta_pan = float(end_pan - start_pan)
    delta_tilt = float(end_tilt - start_tilt)
    distance = math.hypot(delta_pan, delta_tilt)
    if distance <= 0.0:
        return int(round(pan_linear)), int(round(tilt_linear))

    # Circular-like arc: perpendicular sinusoidal offset that is zero at both ends.
    normal_pan = -delta_tilt / distance
    normal_tilt = delta_pan / distance
    arc_amplitude = min(220.0, distance * float(arc_strength))
    offset = math.sin(math.pi * progress) * arc_amplitude

    return (
        int(round(pan_linear + (normal_pan * offset))),
        int(round(tilt_linear + (normal_tilt * offset))),
    )


def _smoothstep(value: float) -> float:
    t = max(0.0, min(1.0, float(value)))
    return t * t * (3.0 - 2.0 * t)


def _apply_time_easing(progress: float, easing_seconds: float, duration_seconds: float) -> float:
    p = max(0.0, min(1.0, float(progress)))
    duration = max(0.0, float(duration_seconds))
    if duration <= 0.0:
        return p

    easing = max(0.0, float(easing_seconds))
    if easing <= 0.0:
        return p

    blend = max(0.0, min(1.0, (2.0 * easing) / duration))
    return ((1.0 - blend) * p) + (blend * _smoothstep(p))


def _max_dim_to_byte(max_dim: Any) -> int:
    value = _parse_float(max_dim, 1.0)
    return _clamp_byte(round(max(0.0, min(1.0, value)) * 255.0))


def _invert_easing_for_dimmer(easing_seconds: float, duration_seconds: float) -> float:
    half_duration = max(0.0, float(duration_seconds) * 0.5)
    eased = max(0.0, min(half_duration, float(easing_seconds)))
    return half_duration - eased


def _subject_closeness_factor(
    *,
    current_pan: int,
    current_tilt: int,
    subject_pan: int,
    subject_tilt: int,
    approach_start_pan: int,
    approach_start_tilt: int,
    close_ratio: float,
) -> float:
    total_pan = abs(float(subject_pan - approach_start_pan))
    total_tilt = abs(float(subject_tilt - approach_start_tilt))
    if total_pan <= 0.0 and total_tilt <= 0.0:
        return 1.0

    ratio = max(0.01, min(1.0, float(close_ratio)))
    close_pan = max(6.0, total_pan * ratio)
    close_tilt = max(6.0, total_tilt * ratio)

    remaining_pan = abs(float(subject_pan - current_pan))
    remaining_tilt = abs(float(subject_tilt - current_tilt))

    pan_factor = max(0.0, min(1.0, (close_pan - remaining_pan) / close_pan))
    tilt_factor = max(0.0, min(1.0, (close_tilt - remaining_tilt) / close_tilt))

    if pan_factor <= 0.0 or tilt_factor <= 0.0:
        return 0.0

    closeness = min(pan_factor, tilt_factor)

    very_close_pan = max(2.0, close_pan * 0.4)
    very_close_tilt = max(2.0, close_tilt * 0.4)
    if remaining_pan <= very_close_pan and remaining_tilt <= very_close_tilt:
        very_close_mix = 1.0 - max(remaining_pan / very_close_pan, remaining_tilt / very_close_tilt)
        boost = 1.0 + (0.35 * max(0.0, min(1.0, very_close_mix)))
        closeness = min(1.0, closeness * boost)

    return max(0.0, min(1.0, closeness))


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

    duration_seconds = _parse_float(payload.get("duration"), 0.0)
    if duration_seconds <= 0.0:
        duration_seconds = max(1.0 / max(1, fps), (end_frame - start_frame) / float(max(1, fps)))

    total_frames = max(1, int(round(duration_seconds * max(1, fps))))
    progress = (frame_index - start_frame) / float(total_frames)
    progress = max(0.0, min(1.0, progress))

    easing_seconds = _parse_float(payload.get("easing"), 0.0)
    arc_strength = _parse_float(payload.get("arc_strength"), 0.015)
    subject_close_ratio = _parse_float(payload.get("subject_close_ratio"), 0.1)
    eased_progress = _apply_time_easing(progress, easing_seconds, duration_seconds)
    dimmer_easing_seconds = _invert_easing_for_dimmer(easing_seconds, duration_seconds)
    dimmer_progress = _apply_time_easing(progress, dimmer_easing_seconds, duration_seconds)

    if eased_progress <= 0.5:
        leg_progress = eased_progress * 2.0
        pan_next, tilt_next = _circular_lerp_u16(
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
        pan_next, tilt_next = _circular_lerp_u16(
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

    closeness = _subject_closeness_factor(
        current_pan=pan_u16,
        current_tilt=tilt_u16,
        subject_pan=subject_pan,
        subject_tilt=subject_tilt,
        approach_start_pan=start_pan,
        approach_start_tilt=start_tilt,
        close_ratio=subject_close_ratio,
    )
    dim_factor = dim_factor * closeness

    max_dim_byte = _max_dim_to_byte(payload.get("max_dim", 1.0))
    intensity = _clamp_byte(round(max_dim_byte * max(0.0, min(1.0, dim_factor))))

    fixture._write_axis_u16_to_universe(universe, "pan", pan_u16)
    fixture._write_axis_u16_to_universe(universe, "tilt", tilt_u16)

    intensity_key = _find_intensity_channel_key(fixture)
    if intensity_key:
        fixture._write_channel(universe, fixture.channels[intensity_key], intensity)

    # Ensure shutter is open during the sweep; dim drives visible intensity.
    if "shutter" in (fixture.channels or {}):
        fixture._write_channel(universe, fixture.channels["shutter"], 255)
