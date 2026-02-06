from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class Fixture(BaseModel, ABC):
    id: str
    name: str
    type: str
    channels: Dict[str, int]
    current_values: Dict[str, Any] = {}
    presets: List[Dict[str, Any]] = []
    effects: List[str] = []
    arm: Dict[str, int] = {}
    meta: Dict[str, Any] = {}
    location: Dict[str, float] = {}

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

    @staticmethod
    def _clamp_byte(value: Any) -> int:
        try:
            iv = int(value)
        except Exception:
            return 0
        return max(0, min(255, iv))

    def _write_channel(self, universe: bytearray, channel_1_based: int, value: Any) -> None:
        if 1 <= channel_1_based <= 512:
            universe[channel_1_based - 1] = self._clamp_byte(value)

    def _render_set_channels(
        self,
        universe: bytearray,
        *,
        channels: Dict[str, Any],
        frame_index: int,
        start_frame: int,
    ) -> None:
        # Instant effect only at its start frame; persistence comes from universe carrying forward.
        if frame_index != start_frame:
            return
        for channel_name, value in channels.items():
            if channel_name in self.channels:
                self._write_channel(universe, self.channels[channel_name], value)

    @abstractmethod
    def render_effect(
        self,
        universe: bytearray,
        *,
        effect: str,
        frame_index: int,
        start_frame: int,
        end_frame: int,
        fps: int,
        data: Dict[str, Any],
        render_state: Dict[str, Any],
    ) -> None:
        """Render a cue effect into the provided DMX universe for the given frame."""
