import math
from typing import Any, Tuple

from .sweep_helpers import clamp_unit, cubic_ease_in, cubic_ease_out


def apply_orbit_easing(progress: float, easing: Any) -> float:
    t = clamp_unit(progress)
    mode = str(easing or "late_focus").strip().lower()
    if mode == "linear":
        return t
    if mode == "early_focus":
        return cubic_ease_out(t)
    if mode == "balanced":
        return (3.0 * t * t) - (2.0 * t * t * t)
    return cubic_ease_in(t)


def spiral_orbit_position(
    *,
    start_pan: int,
    start_tilt: int,
    subject_pan: int,
    subject_tilt: int,
    progress: float,
    orbits: Any,
    easing: Any,
) -> Tuple[int, int]:
    raw_progress = clamp_unit(progress)
    spiral_progress = apply_orbit_easing(raw_progress, easing)
    orbit_count = max(0.0, float(orbits or 0.0))

    delta_pan = float(start_pan - subject_pan)
    delta_tilt = float(start_tilt - subject_tilt)
    radius = math.hypot(delta_pan, delta_tilt)
    if radius <= 0.0:
        return int(subject_pan), int(subject_tilt)

    start_angle = math.atan2(delta_tilt, delta_pan)
    angle = start_angle + (math.tau * orbit_count * raw_progress)
    current_radius = radius * (1.0 - spiral_progress)

    return (
        int(round(subject_pan + (math.cos(angle) * current_radius))),
        int(round(subject_tilt + (math.sin(angle) * current_radius))),
    )