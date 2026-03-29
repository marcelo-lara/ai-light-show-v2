from typing import Any, Dict
from .registry import Effect, REGISTRY
from .fade_in import _get_rgb_channels, _get_dim_channel

class FlashEffect(Effect):
    @property
    def id(self) -> str:
        return "flash"

    @property
    def name(self) -> str:
        return "Flash"

    @property
    def description(self) -> str:
        return "Hits hard at the start and quickly decays, which suits spikes, accents, and transient energy."

    @property
    def tags(self) -> list[str]:
        return ["spike", "accent", "hard", "short"]

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channels": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": True,
        }

    def supports(self, fixture: Any) -> bool:
        meta = getattr(fixture, "meta_channels", {})
        return any(k in meta for k in ["dim", "rgb"])

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
        duration_frames = max(1, end_frame - start_frame)
        progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))
        level = int(round(255 * (1.0 - progress)))

        payload = data or {}
        custom_channels = payload.get("channels")
        
        if isinstance(custom_channels, list):
            channel_names = [str(x) for x in custom_channels]
            for ch in channel_names:
                if ch in fixture.channels:
                    fixture._write_channel(universe, ch, level)
            return

        dim_ch = _get_dim_channel(fixture)
        if dim_ch and dim_ch in fixture.channels:
            fixture._write_channel(universe, dim_ch, level)
            
            meta = getattr(fixture, "meta_channels", {})
            if "shutter" in meta:
                shutter_ch = meta["shutter"].channel
                if shutter_ch and shutter_ch in fixture.channels:
                    open_val = getattr(meta["shutter"], "open_value", 255) or 255
                    fixture._write_channel(universe, shutter_ch, open_val)

        from ..rgb_utils import resolve_rgb_value
        rgb_chs = _get_rgb_channels(fixture)
        
        target_rgb = (255, 255, 255)
        if "color" in payload:
            mapping = fixture.template.mappings.get("color") if hasattr(fixture.template, "mappings") else {}
            resolved = resolve_rgb_value(payload["color"], mapping)
            if resolved and len(resolved) >= 3:
                target_rgb = tuple(resolved[:3])

        # If we have a dimmer, we can just set the color and let the dimmer handle the fade.
        # If we do NOT have a dimmer, we fade the color channels themselves.
        fade_color = not bool(dim_ch and dim_ch in fixture.channels)
        for i, ch in enumerate(rgb_chs):
            if i < 3 and ch in fixture.channels:
                c_level = target_rgb[i]
                if fade_color:
                    c_level = int(round(c_level * (1.0 - progress)))
                fixture._write_channel(universe, ch, c_level)

REGISTRY.register(FlashEffect())
