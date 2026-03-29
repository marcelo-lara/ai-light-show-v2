# pyright: reportAttributeAccessIssue=false

import asyncio
import contextlib
from time import perf_counter
from typing import Optional


class StatePlaybackTransportMixin:
    async def set_playback_state(self, is_playing: bool) -> None:
        task_to_cancel: Optional[asyncio.Task] = None
        async with self.lock:
            current_timecode = self._current_playback_timecode_locked(perf_counter())
            self.is_playing = bool(is_playing)
            if self.is_playing:
                self.timecode = current_timecode
                self.playback_anchor_timecode = current_timecode
                self.playback_anchor_perf = perf_counter()
                if self.preview_task:
                    task_to_cancel = self.preview_task
                self.preview_active = False
                self.preview_task = None
                self.preview_canvas = None
                self.preview_request_id = None
                self.preview_fixture_id = None
                self.preview_effect = None
                self.preview_duration = 0.0
                self.current_frame_index = self._time_to_frame_index(self.timecode)
                self._apply_canvas_frame_to_output(self.current_frame_index)
            elif not self.preview_active:
                self.timecode = current_timecode
                self.playback_anchor_timecode = current_timecode
                self.playback_anchor_perf = perf_counter()
                self.output_universe[:] = self.editor_universe

        if task_to_cancel:
            task_to_cancel.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task_to_cancel

    async def seek_timecode(self, timecode: float) -> None:
        async with self.lock:
            self.timecode = self._clamp_timecode(float(timecode or 0.0))
            self.playback_anchor_timecode = self.timecode
            self.playback_anchor_perf = perf_counter()
            self.current_frame_index = self._time_to_frame_index(self.timecode)
            if self.preview_active and not self.is_playing:
                return
            self._apply_canvas_frame_to_output(self.current_frame_index)

    async def update_timecode(self, timecode: float) -> None:
        async with self.lock:
            self.timecode = self._clamp_timecode(float(timecode or 0.0))
            self.playback_anchor_timecode = self.timecode
            self.playback_anchor_perf = perf_counter()
            self.current_frame_index = self._time_to_frame_index(self.timecode)
            self._apply_canvas_frame_to_output(self.current_frame_index)

    async def advance_timecode(self, delta_seconds: float) -> None:
        async with self.lock:
            if not self.is_playing:
                return
            next_timecode = self._current_playback_timecode_locked(perf_counter())
            if self.song_length_seconds > 0.0 and next_timecode >= self.song_length_seconds:
                self.timecode = float(self.song_length_seconds)
                self.playback_anchor_timecode = self.timecode
                self.playback_anchor_perf = perf_counter()
                self.is_playing = False
            else:
                self.timecode = next_timecode
            self.current_frame_index = self._time_to_frame_index(self.timecode)
            self._apply_canvas_frame_to_output(self.current_frame_index)

    async def blackout_output(self) -> None:
        async with self.lock:
            self.output_universe[:] = bytearray(len(self.output_universe))

    def _time_to_frame_index(self, timecode: float) -> int:
        if not self.canvas:
            return 0
        frame = int(round(float(timecode) * float(self.canvas.fps)))
        return self.canvas.clamp_frame_index(frame)

    def _clamp_timecode(self, timecode: float) -> float:
        clamped = max(0.0, float(timecode or 0.0))
        if self.song_length_seconds > 0.0:
            return min(clamped, float(self.song_length_seconds))
        return clamped

    def _current_playback_timecode_locked(self, now: float) -> float:
        if not self.is_playing:
            return self._clamp_timecode(self.timecode)
        elapsed = max(0.0, float(now) - float(self.playback_anchor_perf))
        return self._clamp_timecode(self.playback_anchor_timecode + elapsed)

    def _apply_canvas_frame_to_output(self, frame_index: int) -> None:
        if not self.canvas:
            return
        self.output_universe[:] = self.canvas.frame_view(frame_index)
