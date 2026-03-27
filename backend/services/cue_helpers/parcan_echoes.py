from __future__ import annotations

from typing import Any, Dict, List

from services.cue_helpers.timing import beats_to_seconds


def _parse_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_unit(value: Any, default: float) -> float:
    return max(0.0, min(1.0, _parse_float(value, default)))


def generate_parcan_echoes(bpm: float, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    payload = params or {}
    if float(bpm) <= 0.0:
        raise ValueError("bpm_unavailable")

    start_time_s = max(0.0, _parse_float(payload.get("start_time_ms"), 0.0) / 1000.0)
    initial_value = _clamp_unit(payload.get("initial_value"), 1.0)
    minimum_value = _clamp_unit(payload.get("minimum_value"), 0.2)
    decay_factor = _clamp_unit(payload.get("decay_factor"), 0.7)
    delay_beats = max(0.125, _parse_float(payload.get("delay_beats"), 0.5))
    flash_duration_beats = max(0.125, _parse_float(payload.get("flash_duration_beats"), 0.25))
    color = str(payload.get("color") or "#FFFFFF").strip() or "#FFFFFF"

    if initial_value <= 0.0:
        raise ValueError("initial_value_must_be_positive")
    if decay_factor <= 0.0 or decay_factor >= 1.0:
        raise ValueError("decay_factor_out_of_range")

    delay_s = beats_to_seconds(delay_beats, bpm)
    duration_s = beats_to_seconds(flash_duration_beats, bpm)
    entries: List[Dict[str, Any]] = []
    fixtures = ["parcan_l", "parcan_r"]

    time_s = start_time_s
    brightness = initial_value
    index = 0
    while index == 0 or brightness >= minimum_value:
        entries.append({
            "time": time_s,
            "fixture_id": fixtures[index % len(fixtures)],
            "effect": "flash",
            "duration": duration_s,
            "data": {
                "color": color,
                "brightness": brightness,
            },
        })
        brightness *= decay_factor
        time_s += delay_s
        index += 1

    return entries