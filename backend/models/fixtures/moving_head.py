from typing import Any, Dict
from .fixture import Fixture


class MovingHead(Fixture):
    type: str = "moving_head"

    def to_dmx(self) -> Dict[int, int]:
        dmx: Dict[int, int] = {}
        for name, ch in self.channels.items():
            raw = self.current_values.get(name, 0) or 0
            if name in ("pan", "tilt"):
                max_deg = int(self.meta.get(f"{name}_range", 540))
                val = int(max(0, min(max_deg, float(raw))) * 255 / (max_deg if max_deg else 1))
            else:
                val = int(raw)
            dmx[ch] = max(0, min(255, val))
        return dmx

    def apply_preset(self, preset: Dict[str, Any]) -> None:
        for k, v in preset.items():
            if k in self.channels:
                if k in ("pan", "tilt"):
                    self.current_values[k] = float(v)
                else:
                    self.set_channel_value(k, v)

    def _deg_to_byte(self, axis: str, degrees: Any) -> int:
        try:
            deg = float(degrees)
        except Exception:
            return 0
        max_deg = int(self.meta.get(f"{axis}_range", 540))
        if max_deg <= 0:
            max_deg = 540
        deg = max(0.0, min(float(max_deg), deg))
        return int(round(deg * 255.0 / float(max_deg)))

    def render_action(
        self,
        universe: bytearray,
        *,
        action: str,
        frame_index: int,
        start_frame: int,
        end_frame: int,
        fps: int,
        data: Dict[str, Any],
        render_state: Dict[str, Any],
    ) -> None:
        action = (action or "").lower().strip()

        if action == "set_channels":
            channels = (data or {}).get("channels", {})
            if isinstance(channels, dict):
                self._render_set_channels(universe, channels=channels, frame_index=frame_index, start_frame=start_frame)
            return

        if action == "move_to":
            # Moving head move_to: interpolate pan/tilt.
            if not ("pan" in self.channels and "tilt" in self.channels):
                return

            duration_frames = max(1, end_frame - start_frame)
            progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))

            # Preferred: degrees (0..range). Also accept raw bytes via pan_byte/tilt_byte.
            if "pan_byte" in (data or {}) or "tilt_byte" in (data or {}):
                target_pan = self._clamp_byte((data or {}).get("pan_byte", 0))
                target_tilt = self._clamp_byte((data or {}).get("tilt_byte", 0))
            else:
                target_pan = self._deg_to_byte("pan", (data or {}).get("pan", 0.0))
                target_tilt = self._deg_to_byte("tilt", (data or {}).get("tilt", 0.0))

            # Cache start pan/tilt once per entry.
            if "start_pan" not in render_state or "start_tilt" not in render_state:
                render_state["start_pan"] = int(universe[self.channels["pan"] - 1])
                render_state["start_tilt"] = int(universe[self.channels["tilt"] - 1])
            start_pan = int(render_state.get("start_pan", 0))
            start_tilt = int(render_state.get("start_tilt", 0))

            pan_val = int(round(start_pan + (target_pan - start_pan) * progress))
            tilt_val = int(round(start_tilt + (target_tilt - start_tilt) * progress))

            self._write_channel(universe, self.channels["pan"], pan_val)
            self._write_channel(universe, self.channels["tilt"], tilt_val)
            return

        if action == "flash":
            # Many moving heads have a dimmer channel; prefer it.
            if "dimmer" not in self.channels:
                return
            duration_frames = max(1, end_frame - start_frame)
            progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))
            level = int(round(255 * (1.0 - progress)))
            self._write_channel(universe, self.channels["dimmer"], level)
            return

    def move_to(self, pan: float, tilt: float) -> None:
        pass

    def arm_fixture(self) -> None:
        # Send arm values
        for channel_name, value in self.arm.items():
            if channel_name in self.channels:
                channel_num = self.channels[channel_name]
                self.current_values[channel_name] = value
