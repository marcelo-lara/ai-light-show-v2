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


def clamp_unit(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


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


def cubic_ease_in(value: float) -> float:
    t = clamp_unit(value)
    return t * t * t


def cubic_ease_out(value: float) -> float:
    t = clamp_unit(value)
    inverse = 1.0 - t
    return 1.0 - (inverse * inverse * inverse)


def apply_leg_easing(progress: float, easing_seconds: float, leg_duration_seconds: float, *, ease_in: bool) -> float:
    p = clamp_unit(progress)
    duration = max(0.0, float(leg_duration_seconds))
    if duration <= 0.0:
        return p

    easing = max(0.0, float(easing_seconds))
    if easing <= 0.0:
        return p

    blend = clamp_unit(easing / duration)
    curve = cubic_ease_in(p) if ease_in else cubic_ease_out(p)
    return ((1.0 - blend) * p) + (blend * curve)


def max_dim_to_byte(max_dim: Any) -> int:
    value = parse_float(max_dim, 1.0)
    return clamp_byte(round(max(0.0, min(1.0, value)) * 255.0))


def apply_dimmer_envelope(progress: float, dimmer_easing: float) -> float:
    p = clamp_unit(progress)
    fade_start = clamp_unit(dimmer_easing)
    fade_span = 1.0 - fade_start

    if p <= 0.5:
        approach_progress = p * 2.0
        if approach_progress <= fade_start:
            return 0.0
        if fade_span <= 0.0:
            return 0.0
        return clamp_unit((approach_progress - fade_start) / fade_span)

    depart_progress = (p - 0.5) * 2.0
    if depart_progress <= 0.0:
        return 1.0
    if fade_span <= 0.0:
        return 0.0
    return clamp_unit(1.0 - (depart_progress / fade_span))
