from typing import Any, Dict
from .registry import Effect, REGISTRY

class FullEffect(Effect):
    @property
    def id(self) -> str:
        return "full"

    @property
    def name(self) -> str:
        return "Full Intensity"

    @property
    def description(self) -> str:
        return "Brings the fixture fully on immediately for bold holds, strong accents, or saturated washes."

    @property
    def tags(self) -> list[str]:
        return ["sustain", "accent", "wash", "hard", "static"]

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def supports(self, fixture: Any) -> bool:
        meta = getattr(fixture, "meta_channels", {})
        return any(k in meta for k in ["dim", "shutter", "rgb"])

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
            return  # Only fire on the exact start frame

        meta = getattr(fixture, "meta_channels", {})

        # Max out dimmer
        if "dim" in meta:
            channel = meta["dim"].channel
            if channel and channel in fixture.channels:
                fixture._write_channel(universe, channel, 255)
        
        # Open shutter
        if "shutter" in meta:
            channel = meta["shutter"].channel
            if channel and channel in fixture.channels:
                # Assuming shutter open is 255
                open_val = getattr(meta["shutter"], "open_value", 255) or 255
                fixture._write_channel(universe, channel, open_val)
        
        # Max out rgb mapping if present
        if "rgb" in meta:
            channels = meta["rgb"].channels
            if channels:
                for channel in channels:
                    if channel in fixture.channels:
                        fixture._write_channel(universe, channel, 255)

REGISTRY.register(FullEffect())
