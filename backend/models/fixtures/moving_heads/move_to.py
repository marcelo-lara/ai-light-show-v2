from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Moving head move_to: interpolate 16-bit pan/tilt (MSB/LSB).
    if not (self._has_axis_16bit("pan") and self._has_axis_16bit("tilt")):
        return

    target_pan_u16, target_tilt_u16 = self._parse_pan_tilt_targets_u16(data or {})
    if target_pan_u16 is None or target_tilt_u16 is None:
        return

    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))

    # Cache start pan/tilt once per entry.
    if "start_pan_u16" not in render_state or "start_tilt_u16" not in render_state:
        render_state["start_pan_u16"] = int(self._read_axis_u16_from_universe(universe, "pan") or 0)
        render_state["start_tilt_u16"] = int(self._read_axis_u16_from_universe(universe, "tilt") or 0)
    start_pan_u16 = int(render_state.get("start_pan_u16", 0))
    start_tilt_u16 = int(render_state.get("start_tilt_u16", 0))

    pan_val = int(round(start_pan_u16 + (int(target_pan_u16) - start_pan_u16) * progress))
    tilt_val = int(round(start_tilt_u16 + (int(target_tilt_u16) - start_tilt_u16) * progress))

    self._write_axis_u16_to_universe(universe, "pan", pan_val)
    self._write_axis_u16_to_universe(universe, "tilt", tilt_val)