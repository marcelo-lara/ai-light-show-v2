from typing import Any, Dict
from colorsys import rgb_to_hsv, hsv_to_rgb
from .registry import Effect, REGISTRY
from .easing import apply_easing
from .fade_in import _get_rgb_channels
from ..rgb_utils import resolve_rgb_value

class ColorFadeEffect(Effect):
    @property
    def id(self) -> str:
        return "color_fade"

    @property
    def name(self) -> str:
        return "Color Fade"

    @property
    def description(self) -> str:
        return "Fades the fixture's color smoothly through the HSV color space rather than linear RGB to avoid muddy transitions."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_color": {"type": "string", "description": "The starting hex color or preset name."},
                "end_color": {"type": "string", "description": "The target hex color or preset name."},
                "easing": {"type": "string", "enum": ["linear", "ease-in", "ease-out", "ease-in-out"]}
            },
            "required": ["end_color"],
            "additionalProperties": False,
        }

    def supports(self, fixture: Any) -> bool:
        meta = getattr(fixture, "meta_channels", {})
        return "rgb" in meta

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

        rgb_chs = _get_rgb_channels(fixture)
        if not rgb_chs or len(rgb_chs) < 3:
            return  # Needs exact red, green, blue mapping structurally.

        if "fade_state" not in render_state:
            mapping = fixture.template.mappings.get("color") if hasattr(fixture.template, "mappings") else {}
            
            # Resolve target
            end_color_raw = payload.get("end_color", "#FFFFFF")
            resolved_end = resolve_rgb_value(end_color_raw, mapping)
            er, eg, eb = resolved_end[0:3] if resolved_end else (255, 255, 255)
            
            # Resolve start
            start_color_raw = payload.get("start_color")
            if start_color_raw is not None:
                resolved_start = resolve_rgb_value(start_color_raw, mapping)
                sr, sg, sb = resolved_start[0:3] if resolved_start else (0, 0, 0)
            else:
                sr = int(universe[fixture.absolute_channels[rgb_chs[0]] - 1]) if rgb_chs[0] in fixture.channels else 0
                sg = int(universe[fixture.absolute_channels[rgb_chs[1]] - 1]) if rgb_chs[1] in fixture.channels else 0
                sb = int(universe[fixture.absolute_channels[rgb_chs[2]] - 1]) if rgb_chs[2] in fixture.channels else 0

            # Convert to HSV (0.0 - 1.0 ranges)
            h1, s1, v1 = rgb_to_hsv(sr / 255.0, sg / 255.0, sb / 255.0)
            h2, s2, v2 = rgb_to_hsv(er / 255.0, eg / 255.0, eb / 255.0)

            # Choose shortest path for Hue
            dh = h2 - h1
            if dh > 0.5:
                dh -= 1.0
            elif dh < -0.5:
                dh += 1.0

            render_state["fade_state"] = {
                "h1": h1, "s1": s1, "v1": v1,
                "dh": dh, "ds": s2 - s1, "dv": v2 - v1
            }

        state = render_state["fade_state"]
        
        # Interpolate
        cur_h = (state["h1"] + state["dh"] * progress) % 1.0
        if cur_h < 0:
            cur_h += 1.0
        cur_s = state["s1"] + state["ds"] * progress
        cur_v = state["v1"] + state["dv"] * progress

        # Convert back
        cr, cg, cb = hsv_to_rgb(cur_h, cur_s, cur_v)
        ir, ig, ib = int(round(cr * 255)), int(round(cg * 255)), int(round(cb * 255))

        if rgb_chs[0] in fixture.channels:
            fixture._write_channel(universe, rgb_chs[0], max(0, min(255, ir)))
        if rgb_chs[1] in fixture.channels:
            fixture._write_channel(universe, rgb_chs[1], max(0, min(255, ig)))
        if rgb_chs[2] in fixture.channels:
            fixture._write_channel(universe, rgb_chs[2], max(0, min(255, ib)))

REGISTRY.register(ColorFadeEffect())
