from typing import Any, Dict
from .registry import Effect, REGISTRY
from .easing import apply_easing
from ..rgb_utils import resolve_rgb_value

def _get_rgb_channels(fixture: Any) -> list[str]:
    meta = getattr(fixture, "meta_channels", {})
    if "rgb" in meta and hasattr(meta["rgb"], "channels"):
        return meta["rgb"].channels
    return []

def _get_dim_channel(fixture: Any) -> str | None:
    meta = getattr(fixture, "meta_channels", {})
    if "dim" in meta:
        return meta["dim"].channel
    return None

class FadeInEffect(Effect):
    @property
    def id(self) -> str:
        return "fade_in"

    @property
    def name(self) -> str:
        return "Fade In"

    @property
    def description(self) -> str:
        return "Fades the fixture's intensity or color from 0 (or a specified start_value) to maximum over the duration."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_value": {"type": ["number", "string", "object"]},
                "easing": {"type": "string", "enum": ["linear", "ease-in", "ease-out", "ease-in-out"]}
            },
            "additionalProperties": True, # To allow legacy arbitrary properties like 'red' for now
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
        payload = data or {}
        easing_type = payload.get("easing", "linear")

        duration_frames = max(1, end_frame - start_frame)
        raw_progress = (frame_index - start_frame) / float(duration_frames)
        # For fade_in (duration=0), snap immediately
        if end_frame <= start_frame:
            raw_progress = 1.0
            if frame_index != start_frame:
                return

        progress = apply_easing(raw_progress, easing_type)

        dim_ch = _get_dim_channel(fixture)
        rgb_chs = _get_rgb_channels(fixture)

        if "start_state" not in render_state:
            # Initialize start state
            start_state = {}
            if dim_ch and dim_ch in fixture.channels:
                # If start_value is explicitly given, try to use it
                sv = payload.get("start_value")
                if sv is not None and isinstance(sv, (int, float)):
                    start_state[dim_ch] = max(0, min(255, int(sv * 255 if isinstance(sv, float) and sv <= 1.0 else sv)))
                else: # Default behavior: start from current universe, but if it's fade_in we often assume starting from 0 unless specified, wait!
                    # Instructions: "if omited, start_value should be the last channel status"
                    start_state[dim_ch] = int(universe[fixture.absolute_channels[dim_ch] - 1])
            
            if rgb_chs:
                # Backward compatibility for mapping {"red": 0.5} etc if not using start_value dict
                sv = payload.get("start_value")
                for ch in rgb_chs:
                    if ch in fixture.channels:
                        if isinstance(sv, dict) and ch in sv:
                            val = sv[ch]
                        else:
                            val = int(universe[fixture.absolute_channels[ch] - 1])
                        
                        if isinstance(val, float) and val <= 1.0:
                            start_state[ch] = max(0, min(255, int(val * 255)))
                        else:
                            start_state[ch] = max(0, min(255, int(val)))

            render_state["start_state"] = start_state

        start_state = render_state["start_state"]

        if dim_ch and dim_ch in start_state:
            start_val = start_state[dim_ch]
            # fade_in target is 255 unless override
            target_val = 255
            legacy_target = payload.get(dim_ch, payload.get("dim", payload.get("dimmer")))
            if legacy_target is not None:
                target_val = int(legacy_target * 255 if isinstance(legacy_target, float) and legacy_target <= 1.0 else legacy_target)

            target_val = max(0, min(255, target_val))
            cur_val = int(round(start_val + (target_val - start_val) * progress))
            fixture._write_channel(universe, dim_ch, cur_val)
        
        for ch in rgb_chs:
            if ch in start_state:
                start_val = start_state[ch]
                target_val = 255 # fade_in target
                # Check if specific target was passed in payload (backward compat)
                override_target = payload.get(ch)
                if override_target is not None:
                    if isinstance(override_target, float) and override_target <= 1.0:
                        target_val = int(override_target * 255)
                    else:
                        target_val = int(override_target)
                
                target_val = max(0, min(255, target_val))
                cur_val = int(round(start_val + (target_val - start_val) * progress))
                fixture._write_channel(universe, ch, cur_val)

        # Open shutter if present
        meta = getattr(fixture, "meta_channels", {})
        if "shutter" in meta and dim_ch:
            channel = meta["shutter"].channel
            if channel and channel in fixture.channels:
                open_val = getattr(meta["shutter"], "open_value", 255) or 255
                fixture._write_channel(universe, channel, open_val)

REGISTRY.register(FadeInEffect())
