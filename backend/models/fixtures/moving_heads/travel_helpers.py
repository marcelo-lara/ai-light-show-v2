from typing import Any

DEFAULT_PAN_FULL_TRAVEL_SECONDS = 2.0
DEFAULT_TILT_FULL_TRAVEL_SECONDS = 0.9
EFFECT_SETTLE_SECONDS = 0.1
EFFECT_SAFETY_PREROLL_SECONDS = 0.1


def fixture_travel_profile_seconds(fixture) -> tuple[float, float]:
    physical_movement = getattr(getattr(fixture, "template", None), "physical_movement", None)
    pan_seconds = getattr(physical_movement, "pan_full_travel_seconds", None)
    tilt_seconds = getattr(physical_movement, "tilt_full_travel_seconds", None)

    try:
        pan_value = float(pan_seconds)
    except (TypeError, ValueError):
        pan_value = DEFAULT_PAN_FULL_TRAVEL_SECONDS

    try:
        tilt_value = float(tilt_seconds)
    except (TypeError, ValueError):
        tilt_value = DEFAULT_TILT_FULL_TRAVEL_SECONDS

    return max(0.0, pan_value), max(0.0, tilt_value)


def max_axis_step_per_frame(fixture, fps: int) -> tuple[float, float]:
    safe_fps = max(1, int(fps))
    pan_seconds, tilt_seconds = fixture_travel_profile_seconds(fixture)
    pan_step = 65535.0 if pan_seconds <= 0.0 else 65535.0 / (pan_seconds * safe_fps)
    tilt_step = 65535.0 if tilt_seconds <= 0.0 else 65535.0 / (tilt_seconds * safe_fps)
    return pan_step, tilt_step


def limit_axis_step(current: Any, target: Any, max_step: float) -> int:
    current_value = float(int(current))
    target_value = float(int(target))
    if max_step <= 0.0:
        return int(round(target_value))
    delta = target_value - current_value
    if delta > max_step:
        return int(round(current_value + max_step))
    if delta < -max_step:
        return int(round(current_value - max_step))
    return int(round(target_value))