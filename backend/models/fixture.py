from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Dict, Any, List


class Fixture(BaseModel, ABC):
    id: str
    name: str
    type: str
    channels: Dict[str, int]
    current_values: Dict[str, Any] = {}
    presets: List[Dict[str, Any]] = []
    actions: List[str] = []
    arm: Dict[str, int] = {}
    meta: Dict[str, Any] = {}

    def set_channel_value(self, channel_name: str, value: int) -> None:
        if channel_name in self.channels:
            self.current_values[channel_name] = max(0, min(255, int(value)))
        else:
            raise KeyError(f"Unknown channel {channel_name}")

    def get_channel_value(self, channel_name: str, default: Any = 0) -> Any:
        return self.current_values.get(channel_name, default)

    @abstractmethod
    def to_dmx(self) -> Dict[int, int]:
        """Convert current_values to DMX mapping: 1-based channel -> 0-255."""

    @abstractmethod
    def apply_preset(self, preset: Dict[str, Any]) -> None:
        """Apply a preset (channel_name -> value) to this fixture."""


class ParcanFixture(Fixture):
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


class MovingHeadFixture(Fixture):
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