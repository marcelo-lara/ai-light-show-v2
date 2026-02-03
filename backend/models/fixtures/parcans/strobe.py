from __future__ import annotations

from typing import Any, Dict


def _warn_once(render_state: Dict[str, Any], key: str, message: str) -> None:
    if render_state.get(key):
        return
    render_state[key] = True
    try:
        print(message, flush=True)
    except Exception:
        pass


def _speed_to_rate_hz(speed: Any) -> float:
    # Map 0..255 to a practical strobe range.
    try:
        s = int(speed)
    except Exception:
        s = 0
    s = max(0, min(255, s))
    # 1..20Hz
    return 1.0 + (float(s) / 255.0) * 19.0


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
    # Parcan strobe: toggles RGB between cached "on" color and 0 at a given rate.
    # RGB-only: dim/program/strobe channels are left untouched.
    payload: Dict[str, Any] = data or {}

    allowed_keys = {"rate", "speed"}
    unknown_keys = sorted([k for k in payload.keys() if k not in allowed_keys])
    if unknown_keys:
        _warn_once(
            render_state,
            "warned_unknown_keys",
            f"[WARN][parcan.strobe] ignoring unknown keys for fixture '{getattr(self, 'id', '?')}': {unknown_keys}",
        )

    if not all(k in self.channels for k in ("red", "green", "blue")):
        _warn_once(
            render_state,
            "warned_no_rgb_channels",
            f"[WARN][parcan.strobe] fixture '{getattr(self, 'id', '?')}' has no RGB channels; no-op",
        )
        return

    # Choose rate.
    if "rate" in payload:
        try:
            rate_hz = float(payload.get("rate") or 0.0)
        except Exception:
            rate_hz = 10.0
    else:
        rate_hz = _speed_to_rate_hz(payload.get("speed", 255))
    if rate_hz <= 0.0:
        rate_hz = 10.0

    # Cache the "on" RGB values once per entry.
    if "on_rgb" not in render_state:
        render_state["on_rgb"] = {
            "red": int(universe[self.channels["red"] - 1]),
            "green": int(universe[self.channels["green"] - 1]),
            "blue": int(universe[self.channels["blue"] - 1]),
        }
    on_rgb = render_state.get("on_rgb") or {}

    # End the strobe on the original color so it persists naturally.
    if frame_index >= end_frame:
        for c in ("red", "green", "blue"):
            self._write_channel(universe, self.channels[c], int(on_rgb.get(c, 0)))
        return

    # Toggle every half period.
    half_period_frames = max(1, int(round(float(fps) / (float(rate_hz) * 2.0))))
    elapsed = max(0, frame_index - start_frame)
    is_on = ((elapsed // half_period_frames) % 2) == 0

    if is_on:
        for c in ("red", "green", "blue"):
            self._write_channel(universe, self.channels[c], int(on_rgb.get(c, 0)))
    else:
        for c in ("red", "green", "blue"):
            self._write_channel(universe, self.channels[c], 0)