from typing import Any, Dict
from .registry import Effect, REGISTRY

class BlackoutEffect(Effect):
    @property
    def id(self) -> str:
        return "blackout"

    @property
    def name(self) -> str:
        return "Blackout"

    @property
    def description(self) -> str:
        return "Instantly drops the fixture's intensity or color to 0."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def supports(self, fixture: Any) -> bool:
        # Supports if there's a dimmer, shutter, or rgb
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

        # If it has a dimmer or shutter, zero it out
        for key in ["dim", "shutter"]:
            if key in meta:
                channel = meta[key].channel
                if channel and channel in fixture.channels:
                    fixture._write_channel(universe, channel, 0)
        
        # Also zero out rgb mapping if present, assuming no independent dimmer
        if "rgb" in meta:
            channels = meta["rgb"].channels
            if channels:
                for channel in channels:
                    if channel in fixture.channels:
                        fixture._write_channel(universe, channel, 0)

REGISTRY.register(BlackoutEffect())
