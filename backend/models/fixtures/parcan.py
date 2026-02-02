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