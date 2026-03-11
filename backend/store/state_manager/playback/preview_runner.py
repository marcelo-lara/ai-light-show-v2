# pyright: reportAttributeAccessIssue=false

import asyncio

from ..constants import FPS


class StatePlaybackPreviewRunnerMixin:
    async def _run_preview(self, request_id: str) -> None:
        try:
            async with self.lock:
                if not self.preview_canvas or self.preview_request_id != request_id:
                    return
                total_frames = self.preview_canvas.total_frames

            for frame_index in range(total_frames):
                async with self.lock:
                    if self.preview_request_id != request_id or not self.preview_canvas:
                        return
                    if self.is_playing:
                        return
                    self.output_universe[:] = self.preview_canvas.frame_view(frame_index)

                if frame_index + 1 < total_frames:
                    await asyncio.sleep(1.0 / FPS)
        except asyncio.CancelledError:
            raise
        finally:
            async with self.lock:
                if self.preview_request_id != request_id:
                    return

                final_frame = None
                if self.preview_canvas and self.preview_canvas.total_frames > 0:
                    final_frame = bytearray(
                        self.preview_canvas.frame_view(self.preview_canvas.total_frames - 1)
                    )

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
                elif final_frame is not None:
                    self.editor_universe[:] = final_frame
                    self.output_universe[:] = final_frame
                else:
                    self.output_universe[:] = self.editor_universe
