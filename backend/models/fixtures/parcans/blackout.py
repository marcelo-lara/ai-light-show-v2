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
    del end_frame, fps, data, render_state
    if frame_index != start_frame:
        return
    for channel_name in ("red", "green", "blue"):
        if channel_name in self.channels:
            self._write_channel(universe, channel_name, 0)
