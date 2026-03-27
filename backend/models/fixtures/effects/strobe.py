from typing import Any, Dict
from .registry import Effect, REGISTRY
from .fade_in import _get_rgb_channels, _get_dim_channel

def _speed_to_rate_hz(speed: Any) -> float:
    try:
        s = int(speed)
    except Exception:
        s = 0
    s = max(0, min(255, s))
    return 1.0 + (float(s) / 255.0) * 19.0

class StrobeEffect(Effect):
    @property
    def id(self) -> str:
        return "strobe"

    @property
    def name(self) -> str:
        return "Strobe"

    @property
    def description(self) -> str:
        return "Toggles the fixture's intensity or color on and off at a specified rate (in Hz) or speed (0-255)."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rate": {"type": "number", "description": "Strobe frequency in Hz."},
                "speed": {"type": "number", "description": "Strobe speed scale from 0 to 255."},
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
        payload = data or {}
        
        if "rate" in payload:
            try:
                rate_hz = float(payload.get("rate") or 0.0)
            except Exception:
                rate_hz = 10.0
        else:
            rate_hz = _speed_to_rate_hz(payload.get("speed", 255))
            
        if rate_hz <= 0.0:
            rate_hz = 10.0

        dim_ch = _get_dim_channel(fixture)
        rgb_chs = _get_rgb_channels(fixture)

        if "on_state" not in render_state:
            state = {}
            if rgb_chs:
                for ch in rgb_chs:
                    if ch in fixture.channels:
                        state[ch] = int(universe[fixture.absolute_channels[ch] - 1])
            render_state["on_state"] = state

        on_state = render_state.get("on_state", {})

        # Return to original or zero on end frame
        if frame_index >= end_frame:
            if dim_ch and dim_ch in fixture.channels:
                fixture._write_channel(universe, dim_ch, 0)
            for ch in rgb_chs:
                if ch in fixture.channels:
                    fixture._write_channel(universe, ch, int(on_state.get(ch, 0)))
            return

        half_period_frames = max(1, int(round(float(fps) / (float(rate_hz) * 2.0))))
        elapsed = max(0, frame_index - start_frame)
        is_on = ((elapsed // half_period_frames) % 2) == 0

        # Dedicated shutter channel override logic? 
        # Typically software strobe ignores hardware strobe channel for direct control, as implemented previously.
        if dim_ch and dim_ch in fixture.channels:
            fixture._write_channel(universe, dim_ch, 255 if is_on else 0)
            meta = getattr(fixture, "meta_channels", {})
            if "shutter" in meta:
                shutter_ch = meta["shutter"].channel
                if shutter_ch and shutter_ch in fixture.channels:
                    open_val = getattr(meta["shutter"], "open_value", 255) or 255
                    fixture._write_channel(universe, shutter_ch, open_val)
        else:
            for ch in rgb_chs:
                if ch in fixture.channels:
                    fixture._write_channel(universe, ch, int(on_state.get(ch, 255)) if is_on else 0)

REGISTRY.register(StrobeEffect())
