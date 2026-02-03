from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Flash: fade the dimmer down to 0 across duration.
    dim_key = None
    for k in ("dim", "dimmer", "intensity"):
        if k in self.channels:
            dim_key = k
            break
    if not dim_key:
        return
    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))
    level = int(round(255 * (1.0 - progress)))
    self._write_channel(universe, self.channels[dim_key], level)