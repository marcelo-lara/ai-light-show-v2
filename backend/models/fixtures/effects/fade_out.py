from typing import Any, Dict
from .registry import Effect, REGISTRY
from .easing import apply_easing
from .fade_in import _get_rgb_channels, _get_dim_channel

class FadeOutEffect(Effect):
    @property
    def id(self) -> str:
        return "fade_out"

    @property
    def name(self) -> str:
        return "Fade Out"

    @property
    def description(self) -> str:
        return "Fades the fixture's intensity or color from its current state (or a specified start_value) to 0 over the duration."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_value": {"type": ["number", "string", "object"]},
                "easing": {"type": "string", "enum": ["linear", "ease-in", "ease-out", "ease-in-out"]}
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
        easing_type = payload.get("easing", "linear")

        duration_frames = max(1, end_frame - start_frame)
        raw_progress = (frame_index - start_frame) / float(duration_frames)
        if end_frame <= start_frame:
            raw_progress = 1.0
            if frame_index != start_frame:
                return

        progress = apply_easing(raw_progress, easing_type)

        dim_ch = _get_dim_channel(fixture)
        rgb_chs = _get_rgb_channels(fixture)

        if "start_state" not in render_state:
            start_state = {}
            if dim_ch and dim_ch in fixture.channels:
                sv = payload.get("start_value")
                if sv is not None and isinstance(sv, (int, float)):
                    start_state[dim_ch] = max(0, min(255, int(sv * 255 if isinstance(sv, float) and sv <= 1.0 else sv)))
                else: 
                    # Backward compatibility for 'dim' payload
                    legacy_sv = payload.get(dim_ch, payload.get("dim"))
                    if legacy_sv is not None:
                        start_state[dim_ch] = max(0, min(255, int(legacy_sv * 255 if isinstance(legacy_sv, float) and legacy_sv <= 1.0 else legacy_sv)))
                    else:
                        start_state[dim_ch] = int(universe[fixture.absolute_channels[dim_ch] - 1])
            
            if rgb_chs:
                sv = payload.get("start_value")
                for ch in rgb_chs:
                    if ch in fixture.channels:
                        if isinstance(sv, dict) and ch in sv:
                            val = sv[ch]
                        else:
                            # Backward compat: payload channel key is start value for fade_out
                            legacy_sv = payload.get(ch)
                            if legacy_sv is not None:
                                val = legacy_sv
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
            target_val = 0
            cur_val = int(round(start_val + (target_val - start_val) * progress))
            fixture._write_channel(universe, dim_ch, cur_val)
        
        for ch in rgb_chs:
            if ch in start_state:
                start_val = start_state[ch]
                target_val = 0 
                cur_val = int(round(start_val + (target_val - start_val) * progress))
                fixture._write_channel(universe, ch, cur_val)

REGISTRY.register(FadeOutEffect())
