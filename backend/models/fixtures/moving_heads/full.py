from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Full: instant full-on of primary output channels (dimmer/shutter) at start frame.
    # Be permissive about channel naming: fixtures commonly use 'dim' or 'dimmer' (or 'intensity').
    if frame_index != start_frame:
        return
    # Prefer common dimmer names in order of likelihood.
    for dim_key in ("dim", "dimmer", "intensity"):
        if dim_key in self.channels:
            self._write_channel(universe, self.channels[dim_key], 255)
            break
    if "shutter" in self.channels:
        self._write_channel(universe, self.channels["shutter"], 255)