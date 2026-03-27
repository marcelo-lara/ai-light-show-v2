from typing import Any, Dict
from .registry import Effect, REGISTRY

class SetChannelsEffect(Effect):
    @property
    def id(self) -> str:
        return "set_channels"

    @property
    def name(self) -> str:
        return "Set Channels"

    @property
    def description(self) -> str:
        return "Instantly sets explicit raw channel values on the fixture."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channels": {
                    "type": "object",
                    "description": "Dictionary mapping channel names to 0-255 values."
                }
            },
            "additionalProperties": True,
        }

    def supports(self, fixture: Any) -> bool:
        return True # Globally supported.

    def render(
        self,
        fixture: Any,
        universe: bytearray,
        *,
        frame_index: int,
        start_frame: int,
        end_frame: int,
        fps: int,
        data: Dict[str, Any],
        render_state: Dict[str, Any],
    ) -> None:
        if frame_index != start_frame:
            return

        payload = data or {}
        channels_map = payload.get("channels", {})
        
        # Legacy support: top-level channels mapping sometimes exists
        for key, value in payload.items():
            if key in fixture.channels:
                channels_map[key] = value

        for k, v in channels_map.items():
            if k in fixture.channels:
                fixture._write_channel(universe, k, v)

REGISTRY.register(SetChannelsEffect())
