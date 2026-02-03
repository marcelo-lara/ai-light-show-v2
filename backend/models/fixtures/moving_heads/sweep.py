import math
from typing import Any, Dict, Optional, Tuple


def _clamp_byte(value: Any) -> int:
    try:
        iv = int(value)
    except Exception:
        return 0
    return max(0, min(255, iv))


def _parse_int(value: Any, default: Optional[int] = 0) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return default


def _lerp_u16(a: int, b: int, t: float) -> int:
    t = max(0.0, min(1.0, float(t)))
    return int(round(a + (b - a) * t))


def _find_intensity_channel_key(fixture) -> Optional[str]:
    for k in ("dim", "dimmer", "intensity"):
        if k in (fixture.channels or {}):
            return k
    return None


def _compute_start_end(
    *,
    center: int,
    span: int,
    start_override: Optional[int],
    end_override: Optional[int],
) -> Tuple[int, int]:
    if start_override is not None and end_override is not None:
        return start_override, end_override

    half = int(span / 2)
    return center - half, center + half


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
    # Sweep: fly across a target (preset or explicit u16 pan/tilt),
    # with a smooth dim envelope peaking when passing over the target.

    total = max(1, end_frame - start_frame)
    p = (frame_index - start_frame) / float(total)
    p = max(0.0, min(1.0, p))

    # Target center pan/tilt (prefer preset if provided).
    center_pan, center_tilt = fixture._parse_pan_tilt_targets_u16(data or {})

    # Fallback: if no target is provided, sweep around current values.
    if center_pan is None:
        center_pan = fixture._read_axis_u16_from_universe(universe, "pan") or 0
    if center_tilt is None:
        center_tilt = fixture._read_axis_u16_from_universe(universe, "tilt") or 0

    # Span (signed allowed; negative flips direction).
    span_pan = _parse_int((data or {}).get("span_pan", 20000), 20000)
    span_tilt = _parse_int((data or {}).get("span_tilt", 0), 0)

    start_pan_override = (data or {}).get("start_pan")
    end_pan_override = (data or {}).get("end_pan")
    start_tilt_override = (data or {}).get("start_tilt")
    end_tilt_override = (data or {}).get("end_tilt")

    start_pan, end_pan = _compute_start_end(
        center=center_pan,
        span=span_pan,
        start_override=_parse_int(start_pan_override, None) if start_pan_override is not None else None,
        end_override=_parse_int(end_pan_override, None) if end_pan_override is not None else None,
    )
    start_tilt, end_tilt = _compute_start_end(
        center=center_tilt,
        span=span_tilt,
        start_override=_parse_int(start_tilt_override, None) if start_tilt_override is not None else None,
        end_override=_parse_int(end_tilt_override, None) if end_tilt_override is not None else None,
    )

    pan_u16 = fixture._clamp_u16(_lerp_u16(start_pan, end_pan, p))
    tilt_u16 = fixture._clamp_u16(_lerp_u16(start_tilt, end_tilt, p))

    fixture._write_axis_u16_to_universe(universe, "pan", pan_u16)
    fixture._write_axis_u16_to_universe(universe, "tilt", tilt_u16)

    # Smooth envelope: 0 -> 1 -> 0 (sinusoidal feels more "analog" than linear).
    intensity = _clamp_byte(round(255 * math.sin(math.pi * p)))

    intensity_key = _find_intensity_channel_key(fixture)
    if intensity_key:
        fixture._write_channel(universe, fixture.channels[intensity_key], intensity)

    # Ensure shutter is open during the sweep; dim drives visible intensity.
    if "shutter" in (fixture.channels or {}):
        fixture._write_channel(universe, fixture.channels["shutter"], 255)
