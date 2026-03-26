from __future__ import annotations

from typing import Any, Dict


def handle(
    self,
    universe: bytearray,
    frame_index: int,
    start_frame: int,
    end_frame: int,
    fps: int,
    data: Dict[str, Any],
    render_state: Dict[str, Any],
) -> None:
    del fps, data
    dim_key = next((key for key in ("dim", "dimmer", "intensity") if key in self.channels), None)
    if not dim_key:
        return

    if "start_dim" not in render_state:
        render_state["start_dim"] = int(universe[self.absolute_channels[dim_key] - 1])
    start_dim = int(render_state.get("start_dim", 0))

    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))
    current_dim = int(round(start_dim * (1.0 - progress)))
    self._write_channel(universe, dim_key, current_dim)

    if "shutter" in self.channels:
        self._write_channel(universe, "shutter", 255 if current_dim > 0 else 0)
