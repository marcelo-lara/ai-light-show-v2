from typing import Dict, Any
from .fixture import Fixture


class Parcan(Fixture):
    type: str = "parcan"

    def to_dmx(self) -> Dict[int, int]:
        dmx: Dict[int, int] = {}
        for name, ch in self.channels.items():
            val = int(self.current_values.get(name, 0) or 0)
            dmx[ch] = max(0, min(255, val))
        return dmx

    def apply_preset(self, preset: Dict[str, Any]) -> None:
        for k, v in preset.items():
            if k in self.channels:
                self.set_channel_value(k, v)

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

        if action == "flash":
            # Parcan flash: fade to 0 across duration.
            duration_frames = max(1, end_frame - start_frame)
            progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))
            level = int(round(255 * (1.0 - progress)))

            channels = (data or {}).get("channels")
            if isinstance(channels, list):
                channel_names = [str(x) for x in channels]
            else:
                # Parcan defaults
                if all(k in self.channels for k in ("red", "green", "blue")):
                    channel_names = ["red", "green", "blue"]
                elif "dimmer" in self.channels:
                    channel_names = ["dimmer"]
                else:
                    channel_names = []

            for channel_name in channel_names:
                if channel_name in self.channels:
                    self._write_channel(universe, self.channels[channel_name], level)
            return