from typing import Dict, Any
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