from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
from .fixture_template import FixtureTemplate, MetaChannel


class Fixture(BaseModel, ABC):
    id: str
    name: str
    base_channel: int
    template: FixtureTemplate
    current_values: Dict[str, Any] = {}
    presets: List[Dict[str, Any]] = []
    poi_targets: Dict[str, Dict[str, Any]] = {}
    location: Dict[str, float] = {}

    @property
    def type(self) -> str:
        return self.template.type

    @property
    def channels(self) -> Dict[str, int]:
        """Returns relative channel offsets from template."""
        return self.template.channels

    @property
    def absolute_channels(self) -> Dict[str, int]:
        """Returns absolute 1-based DMX channels."""
        return {name: self.base_channel + offset for name, offset in self.channels.items()}

    @property
    def meta_channels(self) -> Dict[str, MetaChannel]:
        return self.template.meta_channels

    @property
    def mappings(self) -> Dict[str, Dict[str, Union[int, str]]]:
        return self.template.mappings

    @property
    def effects(self) -> List[str]:
        return self.template.effects

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

    def _write_channel(self, universe: bytearray, channel_name: str, value: Any) -> None:
        if channel_name in self.absolute_channels:
            abs_ch = self.absolute_channels[channel_name]
            if 1 <= abs_ch <= 512:
                universe[abs_ch - 1] = self._clamp_byte(value)

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
                self._write_channel(universe, channel_name, value)

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
