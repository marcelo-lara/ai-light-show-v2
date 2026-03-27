from __future__ import annotations

from models.fixtures.rgb_utils import resolve_rgb_value


def _resolve_level(data) -> int:
    raw = (data or {}).get("brightness", (data or {}).get("intensity", 255))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 255.0
    if 0.0 <= value <= 1.0:
        value *= 255.0
    return max(0, min(255, int(round(value))))


def _resolve_color(self, data):
    payload = data or {}
    target = (255, 255, 255)
    if "color" not in payload:
        return target
    mapping = getattr(getattr(self, "template", None), "mappings", {}).get("color", {})
    resolved = resolve_rgb_value(payload.get("color"), mapping)
    if resolved and len(resolved) >= 3:
        return tuple(int(channel) for channel in resolved[:3])
    return target


def handle(self, universe, frame_index, start_frame, end_frame, fps, data, render_state):
    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))
    level = int(round(_resolve_level(data) * (1.0 - progress)))

    channels = (data or {}).get("channels")
    if isinstance(channels, list):
        channel_names = [str(x) for x in channels]
    else:
        if all(k in self.channels for k in ("red", "green", "blue")):
            channel_names = ["red", "green", "blue"]
        elif "dim" in self.channels:
            channel_names = ["dim"]
        else:
            channel_names = []

    if channel_names == ["red", "green", "blue"]:
        target = _resolve_color(self, data)
        for index, channel_name in enumerate(channel_names):
            if channel_name in self.channels:
                value = int(round(target[index] * (level / 255.0)))
                self._write_channel(universe, channel_name, value)
        if "dim" in self.channels:
            self._write_channel(universe, "dim", level)
        return

    for channel_name in channel_names:
        if channel_name in self.channels:
            self._write_channel(universe, channel_name, level)