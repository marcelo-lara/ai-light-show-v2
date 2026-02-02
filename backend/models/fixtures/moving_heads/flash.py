from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Many moving heads have a dimmer channel; prefer it.
    if "dimmer" not in self.channels:
        return
    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))
    level = int(round(255 * (1.0 - progress)))
    self._write_channel(universe, self.channels["dimmer"], level)