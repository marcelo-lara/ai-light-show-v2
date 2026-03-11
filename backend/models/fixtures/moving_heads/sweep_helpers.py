import math
from typing import Any, Optional, Tuple


def clamp_byte(value: Any) -> int:
    try:
        iv = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(255, iv))


def parse_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def find_intensity_channel_key(fixture) -> Optional[str]:
    for key in ("dim", "dimmer", "intensity"):
        if key in (fixture.channels or {}):
            return key
    return None


def circular_lerp_u16(
    *,
    start_pan: int,
    start_tilt: int,
    end_pan: int,
    end_tilt: int,
    t: float,
    arc_strength: float,
) -> Tuple[int, int]:
    progress = max(0.0, min(1.0, float(t)))

    pan_linear = float(round(start_pan + ((end_pan - start_pan) * progress)))
    tilt_linear = float(round(start_tilt + ((end_tilt - start_tilt) * progress)))
    delta_pan = float(end_pan - start_pan)
    delta_tilt = float(end_tilt - start_tilt)
    distance = math.hypot(delta_pan, delta_tilt)
    if distance <= 0.0:
        return int(round(pan_linear)), int(round(tilt_linear))

    normal_pan = -delta_tilt / distance
    normal_tilt = delta_pan / distance
    arc_amplitude = min(220.0, distance * float(arc_strength))
    offset = math.sin(math.pi * progress) * arc_amplitude

    return (
        int(round(pan_linear + (normal_pan * offset))),
        int(round(tilt_linear + (normal_tilt * offset))),
    )


def smoothstep(value: float) -> float:
    t = max(0.0, min(1.0, float(value)))
    return t * t * (3.0 - 2.0 * t)


def apply_time_easing(progress: float, easing_seconds: float, duration_seconds: float) -> float:
    p = max(0.0, min(1.0, float(progress)))
    duration = max(0.0, float(duration_seconds))
    if duration <= 0.0:
        return p

    easing = max(0.0, float(easing_seconds))
    if easing <= 0.0:
        return p

    blend = max(0.0, min(1.0, (2.0 * easing) / duration))
    return ((1.0 - blend) * p) + (blend * smoothstep(p))


def max_dim_to_byte(max_dim: Any) -> int:
    value = parse_float(max_dim, 1.0)
    return clamp_byte(round(max(0.0, min(1.0, value)) * 255.0))


def invert_easing_for_dimmer(easing_seconds: float, duration_seconds: float) -> float:
    half_duration = max(0.0, float(duration_seconds) * 0.5)
    eased = max(0.0, min(half_duration, float(easing_seconds)))
    return half_duration - eased


def subject_closeness_factor(
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
