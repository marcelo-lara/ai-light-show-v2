from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Full: instant full-on of primary output channels (dimmer/shutter) at start frame.
    # Placeholder: set `dimmer` and/or `shutter` to full when action begins.
    if frame_index != start_frame:
        return
    if "dimmer" in self.channels:
        self._write_channel(universe, self.channels["dimmer"], 255)
    if "shutter" in self.channels:
        self._write_channel(universe, self.channels["shutter"], 255)