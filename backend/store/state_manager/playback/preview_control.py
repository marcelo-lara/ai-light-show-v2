# pyright: reportAttributeAccessIssue=false

import asyncio
import contextlib
from typing import Optional


class StatePlaybackPreviewControlMixin:
    async def cancel_preview(self) -> bool:
        task: Optional[asyncio.Task] = None
        async with self.lock:
            if not self.preview_active and not self.preview_task:
                return False

            task = self.preview_task
            self.preview_active = False
            self.preview_task = None
            self.preview_canvas = None
            self.preview_request_id = None
            self.preview_fixture_id = None
            self.preview_effect = None
            self.preview_duration = 0.0

            if self.is_playing:
                self.current_frame_index = self._time_to_frame_index(self.timecode)
                self._apply_canvas_frame_to_output(self.current_frame_index)
            else:
                self.output_universe[:] = self.editor_universe

        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        return True

    async def wait_for_preview_end(self, request_id: str) -> None:
        task: Optional[asyncio.Task] = None
        async with self.lock:
            if self.preview_request_id != request_id:
                return
            task = self.preview_task
        if task:
            with contextlib.suppress(asyncio.CancelledError):
                await task
