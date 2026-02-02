from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Moving head move_to: interpolate pan/tilt.
    if not ("pan" in self.channels and "tilt" in self.channels):
        return

    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))

    # Preferred: degrees (0..range). Also accept raw bytes via pan_byte/tilt_byte.
    if "pan_byte" in (data or {}) or "tilt_byte" in (data or {}):
        target_pan = self._clamp_byte((data or {}).get("pan_byte", 0))
        target_tilt = self._clamp_byte((data or {}).get("tilt_byte", 0))
    else:
        target_pan = self._deg_to_byte("pan", (data or {}).get("pan", 0.0))
        target_tilt = self._deg_to_byte("tilt", (data or {}).get("tilt", 0.0))

    # Cache start pan/tilt once per entry.
    if "start_pan" not in render_state or "start_tilt" not in render_state:
        render_state["start_pan"] = int(universe[self.channels["pan"] - 1])
        render_state["start_tilt"] = int(universe[self.channels["tilt"] - 1])
    start_pan = int(render_state.get("start_pan", 0))
    start_tilt = int(render_state.get("start_tilt", 0))

    pan_val = int(round(start_pan + (target_pan - start_pan) * progress))
    tilt_val = int(round(start_tilt + (target_tilt - start_tilt) * progress))

    self._write_channel(universe, self.channels["pan"], pan_val)
    self._write_channel(universe, self.channels["tilt"], tilt_val)