from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Seek: immediate set of pan/tilt or apply a named preset at the action's start frame.
    # This is a placeholder implementation: it applies presets if `preset` is provided
    # or sets pan/tilt directly from `pan`/`tilt` (degrees) or `pan_byte`/`tilt_byte` (raw).
    if frame_index != start_frame:
        return
    data = data or {}
    preset_name = data.get("preset")
    if preset_name:
        for p in self.presets:
            if p.get("name") == preset_name:
                # apply preset values and write immediate DMX for pan/tilt
                self.apply_preset(p.get("values", {}))
                if "pan" in self.channels:
                    val = self._deg_to_byte("pan", self.current_values.get("pan", 0))
                    self._write_channel(universe, self.channels["pan"], val)
                if "tilt" in self.channels:
                    val = self._deg_to_byte("tilt", self.current_values.get("tilt", 0))
                    self._write_channel(universe, self.channels["tilt"], val)
                return

    # Direct pan/tilt override
    if ("pan_byte" in data or "pan" in data) and "pan" in self.channels:
        pan_val = self._clamp_byte(data.get("pan_byte", self._deg_to_byte("pan", data.get("pan", 0))))
        self._write_channel(universe, self.channels["pan"], pan_val)
    if ("tilt_byte" in data or "tilt" in data) and "tilt" in self.channels:
        tilt_val = self._clamp_byte(data.get("tilt_byte", self._deg_to_byte("tilt", data.get("tilt", 0))))
        self._write_channel(universe, self.channels["tilt"], tilt_val)