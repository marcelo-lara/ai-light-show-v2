from typing import Any, Dict


def _warn_once(render_state: Dict[str, Any], key: str, message: str) -> None:
    if render_state.get(key):
        return
    render_state[key] = True
    try:
        print(message, flush=True)
    except Exception:
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
    # Parcan full: instant set of RGB at start frame.
    # Intentionally RGB-only; dim/other channels are left untouched.
    if frame_index != start_frame:
        return

    payload: Dict[str, Any] = data or {}
    allowed_keys = {"red", "green", "blue"}

    unknown_keys = sorted([k for k in payload.keys() if k not in allowed_keys])
    if unknown_keys:
        _warn_once(
            render_state,
            "warned_unknown_keys",
            f"[WARN][parcan.full] ignoring unknown keys for fixture '{getattr(self, 'id', '?')}': {unknown_keys}",
        )

    if not all(k in self.channels for k in ("red", "green", "blue")):
        _warn_once(
            render_state,
            "warned_no_rgb_channels",
            f"[WARN][parcan.full] fixture '{getattr(self, 'id', '?')}' has no RGB channels; no-op",
        )
        return

    # If any RGB key is provided, treat missing components as 0 for determinism.
    if any(k in payload for k in allowed_keys):
        targets = {
            "red": self._clamp_byte(payload.get("red", 0)),
            "green": self._clamp_byte(payload.get("green", 0)),
            "blue": self._clamp_byte(payload.get("blue", 0)),
        }
    else:
        # Otherwise, full white.
        targets = {"red": 255, "green": 255, "blue": 255}

    for channel_name, value in targets.items():
        self._write_channel(universe, self.channels[channel_name], value)