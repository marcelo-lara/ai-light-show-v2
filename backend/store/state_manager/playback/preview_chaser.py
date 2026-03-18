# pyright: reportAttributeAccessIssue=false

import asyncio
import contextlib
from typing import Any, Dict, List, Optional
from uuid import uuid4

from models.cues import CueEntry, CueSheet
from store.dmx_canvas import DMXCanvas
from store.services.canvas_render_core import iter_cues_for_render, render_entry_into_universe

from ..constants import FPS


class StatePlaybackPreviewChaserMixin:
    def _render_preview_chaser_canvas(self, entries: List[Dict[str, Any]], base_universe: bytearray) -> DMXCanvas:
        cue_sheet = CueSheet(
            song_filename=(getattr(self.current_song, "song_id", None) or "preview"),
            entries=[CueEntry(**entry) for entry in entries],
        )
        cues = iter_cues_for_render(cue_sheet, FPS, [], 0.0)
        total_frames = max(1, max((end for _, end, _ in cues), default=0) + 1)
        canvas = DMXCanvas.allocate(fps=FPS, total_frames=total_frames)
        active: List[tuple[int, int, CueEntry]] = []
        cues_by_start: Dict[int, List[tuple[int, int, CueEntry]]] = {}
        for start, end, entry in cues:
            cues_by_start.setdefault(start, []).append((start, end, entry))
        universe = bytearray(base_universe)
        entry_render_state: Dict[int, Dict[str, Any]] = {}
        for frame_index in range(total_frames):
            if frame_index in cues_by_start:
                active.extend(cues_by_start[frame_index])
            if active:
                active = [item for item in active if item[1] >= frame_index]
                for start_frame, end_frame, entry in sorted(active, key=lambda item: (item[2].time, item[2].fixture_id or "", item[2].effect or "")):
                    render_entry_into_universe(
                        fixtures=self.fixtures,
                        universe=universe,
                        frame_index=frame_index,
                        start_frame=start_frame,
                        end_frame=end_frame,
                        entry=entry,
                        entry_render_state=entry_render_state,
                        fps=FPS,
                    )
            canvas.set_frame(frame_index, universe)
        return canvas

    async def start_preview_chaser(
        self,
        chaser_id: str,
        start_time_ms: float,
        repetitions: int,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cancel_task: Optional[asyncio.Task] = None
        async with self.lock:
            if self.is_playing:
                return {"ok": False, "reason": "playback_active"}
            chaser = self.get_chaser_definition(chaser_id)
            if not chaser:
                return {"ok": False, "reason": "unknown_chaser", "chaser_id": chaser_id}
            bpm = self._current_bpm()
            if bpm <= 0.0:
                return {"ok": False, "reason": "bpm_unavailable"}

            entries = self.expand_chaser_entries(chaser.id, max(0.0, float(start_time_ms)), max(1, int(repetitions)), bpm)
            first_time = min((float(item["time"]) for item in entries), default=0.0)
            normalized = [{**item, "time": max(0.0, float(item["time"]) - first_time)} for item in entries]

            rid = str(request_id or uuid4())
            if self.preview_chaser_task:
                cancel_task = self.preview_chaser_task

            self.preview_chaser_canvas = self._render_preview_chaser_canvas(normalized, bytearray(self.editor_universe))
            self.preview_chaser_request_id = rid
            self.preview_chaser_name = chaser.id
            self.preview_chaser_active = True
            self.output_universe[:] = self.preview_chaser_canvas.frame_view(0)
            self.preview_chaser_task = asyncio.create_task(self._run_preview_chaser(rid))

        if cancel_task:
            cancel_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cancel_task

        return {"ok": True, "requestId": rid, "chaser_id": chaser.id, "entries": len(normalized)}

    async def cancel_preview_chaser(self) -> bool:
        task: Optional[asyncio.Task] = None
        async with self.lock:
            if not self.preview_chaser_active and not self.preview_chaser_task:
                return False
            task = self.preview_chaser_task
            self.preview_chaser_active = False
            self.preview_chaser_task = None
            self.preview_chaser_canvas = None
            self.preview_chaser_request_id = None
            self.preview_chaser_name = None
            self.output_universe[:] = self.editor_universe
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        return True

    async def _run_preview_chaser(self, request_id: str) -> None:
        try:
            async with self.lock:
                if not self.preview_chaser_canvas or self.preview_chaser_request_id != request_id:
                    return
                total_frames = self.preview_chaser_canvas.total_frames
            for frame_index in range(total_frames):
                async with self.lock:
                    if self.preview_chaser_request_id != request_id or not self.preview_chaser_canvas or self.is_playing:
                        return
                    self.output_universe[:] = self.preview_chaser_canvas.frame_view(frame_index)
                if frame_index + 1 < total_frames:
                    await asyncio.sleep(1.0 / FPS)
        finally:
            async with self.lock:
                if self.preview_chaser_request_id != request_id:
                    return
                self.preview_chaser_active = False
                self.preview_chaser_task = None
                self.preview_chaser_canvas = None
                self.preview_chaser_request_id = None
                self.preview_chaser_name = None
                self.output_universe[:] = self.editor_universe
