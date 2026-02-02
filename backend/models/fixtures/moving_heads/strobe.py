from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Strobe: simple placeholder that toggles shutter (or dimmer) on/off at a given rate (Hz).
    # Data: {"rate": <Hz>} defaults to 10Hz.
    if "shutter" not in self.channels and "dimmer" not in self.channels:
        return
    rate = float((data or {}).get("rate", 10.0))
    if rate <= 0.0:
        rate = 10.0
    period_frames = max(1, int(round(float(fps) / rate)))
    elapsed = frame_index - start_frame
    on = ((elapsed // period_frames) % 2) == 0
    value = 255 if on else 0
    channel_name = "shutter" if "shutter" in self.channels else "dimmer"
    self._write_channel(universe, self.channels[channel_name], value)