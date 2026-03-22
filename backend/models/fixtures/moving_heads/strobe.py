from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Strobe is dimmer-driven. Dedicated shutter/strobe channels are not modulated here.
    # Data: {"rate": <Hz>} defaults to 10Hz.
    intensity_key = next((key for key in ("dim", "dimmer", "intensity") if key in self.channels), None)
    if not intensity_key:
        return

    try:
        rate = float((data or {}).get("rate", 10.0) or 10.0)
    except (TypeError, ValueError):
        rate = 10.0
    if rate <= 0.0:
        rate = 10.0
    period_frames = max(1, int(round(float(fps) / rate)))
    elapsed = max(0, frame_index - start_frame)
    on = ((elapsed // period_frames) % 2) == 0

    if frame_index >= end_frame:
        self._write_channel(universe, intensity_key, 0)
        return

    value = 255 if on else 0
    self._write_channel(universe, intensity_key, value)
