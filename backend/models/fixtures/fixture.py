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