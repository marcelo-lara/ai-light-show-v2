from typing import Any, Dict

from .poi_geometry import estimate_circle_pan_tilt
from .travel_helpers import limit_axis_step, max_axis_step_per_frame


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
    if not (fixture._has_axis_16bit("pan") and fixture._has_axis_16bit("tilt")):
        return

    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))
    target_pan_u16, target_tilt_u16 = estimate_circle_pan_tilt(fixture, data or {}, progress)
    if target_pan_u16 is None or target_tilt_u16 is None:
        return

    if "circle_last_pan_u16" not in render_state or "circle_last_tilt_u16" not in render_state:
        render_state["circle_last_pan_u16"] = int(fixture._read_axis_u16_from_universe(universe, "pan") or 0)
        render_state["circle_last_tilt_u16"] = int(fixture._read_axis_u16_from_universe(universe, "tilt") or 0)

    last_pan_u16 = int(render_state.get("circle_last_pan_u16", 0))
    last_tilt_u16 = int(render_state.get("circle_last_tilt_u16", 0))
    max_pan_step, max_tilt_step = max_axis_step_per_frame(fixture, fps)
    pan_value = fixture._clamp_u16(limit_axis_step(last_pan_u16, target_pan_u16, max_pan_step))
    tilt_value = fixture._clamp_u16(limit_axis_step(last_tilt_u16, target_tilt_u16, max_tilt_step))
    fixture._write_axis_u16_to_universe(universe, "pan", pan_value)
    fixture._write_axis_u16_to_universe(universe, "tilt", tilt_value)
    render_state["circle_last_pan_u16"] = int(pan_value)
    render_state["circle_last_tilt_u16"] = int(tilt_value)
