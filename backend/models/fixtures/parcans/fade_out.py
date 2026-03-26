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
    allowed_keys = {"red", "green", "blue"}

    if end_frame <= start_frame:
        if frame_index != start_frame:
            return
        for channel_name in allowed_keys:
            if channel_name in self.channels:
                self._write_channel(universe, channel_name, 0)
        return

    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))

    if "start_rgb" not in render_state:
        start_rgb: Dict[str, int] = {}
        for channel_name in allowed_keys:
            if channel_name in self.channels:
                start_rgb[channel_name] = int(universe[self.absolute_channels[channel_name] - 1])
        render_state["start_rgb"] = start_rgb

    start_rgb = render_state.get("start_rgb", {}) or {}
    for channel_name in allowed_keys:
        if channel_name not in self.channels:
            continue
        start_val = int(start_rgb.get(channel_name, int(universe[self.absolute_channels[channel_name] - 1])))
        cur_val = int(round(start_val * (1.0 - progress)))
        self._write_channel(universe, channel_name, cur_val)
