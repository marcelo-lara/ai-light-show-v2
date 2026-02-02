def handle(self, universe, frame_index, start_frame, end_frame, fps, data, render_state):
    channels = (data or {}).get("channels", {})
    if isinstance(channels, dict):
        self._render_set_channels(universe, channels=channels, frame_index=frame_index, start_frame=start_frame)