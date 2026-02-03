from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Seek: immediate set of 16-bit pan/tilt at the action's start frame.
    if frame_index != start_frame:
        return
    if not (self._has_axis_16bit("pan") and self._has_axis_16bit("tilt")):
        return

    target_pan_u16, target_tilt_u16 = self._parse_pan_tilt_targets_u16(data or {})
    if target_pan_u16 is None or target_tilt_u16 is None:
        return

    self._write_axis_u16_to_universe(universe, "pan", int(target_pan_u16))
    self._write_axis_u16_to_universe(universe, "tilt", int(target_tilt_u16))