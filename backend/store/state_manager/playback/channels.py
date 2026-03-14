# pyright: reportAttributeAccessIssue=false

from store.dmx_canvas import DMX_CHANNELS


class StatePlaybackChannelMixin:
    async def update_dmx_channel(self, channel: int, value: int) -> bool:
        async with self.lock:
            if self.is_playing:
                return False
            if 1 <= channel <= DMX_CHANNELS and 0 <= value <= 255:
                self.editor_universe[channel - 1] = value
                if not self.is_playing and not self.preview_active:
                    self.output_universe[channel - 1] = value
                    return True
            return False
