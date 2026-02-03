def handle(self, universe, frame_index, start_frame, end_frame, fps, data, render_state):
    # Parcan flash: set RGB to 100% then fade to 0 across duration. default duration: 250 ms.
    duration_frames = max(1, end_frame - start_frame)
    progress = max(0.0, min(1.0, (frame_index - start_frame) / float(duration_frames)))
    level = int(round(255 * (1.0 - progress)))

    channels = (data or {}).get("channels")
    if isinstance(channels, list):
        channel_names = [str(x) for x in channels]
    else:
        # Parcan defaults
        if all(k in self.channels for k in ("red", "green", "blue")):
            channel_names = ["red", "green", "blue"]
        elif "dim" in self.channels:
            channel_names = ["dim"]
        else:
            channel_names = []

    for channel_name in channel_names:
        if channel_name in self.channels:
            self._write_channel(universe, self.channels[channel_name], level)