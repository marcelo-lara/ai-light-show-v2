from typing import Any, Dict


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    channels = (data or {}).get("channels", {})
    if isinstance(channels, dict):
        self._render_set_channels(universe, channels=channels, frame_index=frame_index, start_frame=start_frame)