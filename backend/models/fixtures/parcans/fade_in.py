from __future__ import annotations

from typing import Any, Dict


def _warn_once(render_state: Dict[str, Any], key: str, message: str) -> None:
    if render_state.get(key):
        return
    render_state[key] = True
    try:
        print(message, flush=True)
    except Exception:
        # Best-effort only; rendering should never crash due to logging.
        pass


def handle(
    self,
    universe: bytearray,
    frame_index: int,
    start_frame: int,
    end_frame: int,
    fps: int,
    data: Dict[str, Any],
    render_state: Dict[str, Any],
) -> None:
    # Parcan fade_in: interpolate RGB from current DMX values at cue start to targets.
    # RGB-only: never touches dim/other channels.
    payload: Dict[str, Any] = data or {}
    allowed_keys = {"red", "green", "blue"}

    rgb_targets = {k: payload[k] for k in allowed_keys if k in payload}
    unknown_keys = sorted([k for k in payload.keys() if k not in allowed_keys])

    if unknown_keys:
        _warn_once(
            render_state,
            "warned_unknown_keys",
            f"[WARN][parcan.fade_in] ignoring unknown keys for fixture '{getattr(self, 'id', '?')}': {unknown_keys}",
        )

    if not rgb_targets:
        _warn_once(
            render_state,
            "warned_no_rgb",
            f"[WARN][parcan.fade_in] no RGB target values provided for fixture '{getattr(self, 'id', '?')}' (expected red/green/blue)",
        )
        return

    # Instant set when duration is 0 (end_frame == start_frame).
    if end_frame <= start_frame:
        if frame_index != start_frame:
            return
        for channel_name, target in rgb_targets.items():
            if channel_name in self.channels:
                self._write_channel(universe, self.channels[channel_name], self._clamp_byte(target))
        return

    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))

    # Cache start RGB once per entry.
    if "start_rgb" not in render_state:
        start_rgb: Dict[str, int] = {}
        for channel_name in allowed_keys:
            if channel_name in self.channels:
                start_rgb[channel_name] = int(universe[self.channels[channel_name] - 1])
        render_state["start_rgb"] = start_rgb

    start_rgb = render_state.get("start_rgb", {}) or {}

    for channel_name, target in rgb_targets.items():
        if channel_name not in self.channels:
            continue
        start_val = int(start_rgb.get(channel_name, int(universe[self.channels[channel_name] - 1])))
        target_val = self._clamp_byte(target)
        cur_val = int(round(start_val + (target_val - start_val) * progress))
        self._write_channel(universe, self.channels[channel_name], cur_val)