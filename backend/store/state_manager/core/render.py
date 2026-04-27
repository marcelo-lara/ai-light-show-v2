# pyright: reportAttributeAccessIssue=false

import math
from typing import Any, Dict

from models.fixtures.fixture import Fixture
from store.dmx_canvas import DMXCanvas
from store.services.canvas_rendering import (
    dump_canvas_debug,
    render_cue_sheet_to_canvas,
    render_preview_canvas,
)
from store.services.canvas_debug import (
    build_named_canvas_binary_path,
    build_show_name,
    dump_canvas_binary,
    dump_named_canvas_debug,
)

from ..constants import FPS


class StateCoreRenderMixin:
    def _build_canvas_metadata(self, canvas: DMXCanvas, song_filename: str) -> Dict[str, Any]:
        show_name = build_show_name()
        return {
            "song": song_filename,
            "fps": int(canvas.fps),
            "total_frames": int(canvas.total_frames),
            "duration_s": round((max(0, canvas.total_frames - 1)) / float(canvas.fps), 3),
            "show_name": show_name,
            "dmx_binary_path": str(
                build_named_canvas_binary_path(
                    backend_path=self.backend_path,
                    song_filename=song_filename,
                )
            ),
            "dmx_log_path": str(self.backend_path / "cues" / f"{song_filename}.dmx.log"),
        }

    def _render_cue_sheet_to_canvas(self) -> DMXCanvas:
        return render_cue_sheet_to_canvas(
            fixtures=self.fixtures,
            cue_sheet=self.cue_sheet,
            chasers=self.chasers,
            bpm=self._current_bpm(),
            song_length_seconds=self.song_length_seconds,
            fps=FPS,
            apply_arm=self._apply_arm,
        )

    def _render_preview_canvas(
        self,
        *,
        fixture: Fixture,
        effect: str,
        duration: float,
        data: Dict[str, Any],
        base_universe: bytearray,
    ) -> DMXCanvas:
        return render_preview_canvas(
            fixture=fixture,
            effect=effect,
            duration=duration,
            data=data,
            base_universe=base_universe,
            fps=FPS,
        )

    def _dump_canvas_debug(self, song_filename: str) -> None:
        dump_canvas_debug(
            backend_path=self.backend_path,
            song_filename=song_filename,
            canvas=self.canvas,
            max_used_channel=self.max_used_channel,
        )

    def _dump_preview_canvas_debug(self, file_stem: str) -> None:
        dump_named_canvas_debug(
            backend_path=self.backend_path,
            file_stem=file_stem,
            canvas=self.preview_canvas,
            max_used_channel=self.max_used_channel,
        )

    async def rerender_dmx_canvas(self) -> Dict[str, Any]:
        async with self.lock:
            song_filename = getattr(getattr(self, "current_song", None), "song_id", None)
            if not song_filename or not self.cue_sheet:
                return {"ok": False, "reason": "no_song_loaded"}

            self._refresh_canvas_after_cue_change()
            if not self.canvas:
                return {"ok": False, "reason": "canvas_unavailable"}

            dump_canvas_binary(
                backend_path=self.backend_path,
                song_filename=song_filename,
                canvas=self.canvas,
            )

            return {
                "ok": True,
                **self._build_canvas_metadata(self.canvas, song_filename),
            }

    async def read_fixture_output_window(
        self,
        fixture_id: str,
        start_time: float,
        end_time: float,
        max_samples: int = 240,
    ) -> Dict[str, Any]:
        async with self.lock:
            if end_time < start_time:
                return {"ok": False, "reason": "invalid_time_range"}
            if not self.canvas:
                return {"ok": False, "reason": "canvas_unavailable"}

            fixture = self._get_fixture(str(fixture_id or "").strip())
            if not fixture:
                return {"ok": False, "reason": "fixture_not_found", "fixture_id": fixture_id}

            canvas = self.canvas
            start_frame = canvas.clamp_frame_index(int(math.floor(float(start_time) * canvas.fps)))
            end_frame = canvas.clamp_frame_index(int(math.ceil(float(end_time) * canvas.fps)))
            frame_count = max(1, end_frame - start_frame + 1)
            sample_limit = max(1, min(int(max_samples or 1), frame_count))
            step = max(1, int(math.ceil(frame_count / float(sample_limit))))

            sample_indices = list(range(start_frame, end_frame + 1, step))
            if sample_indices[-1] != end_frame:
                sample_indices.append(end_frame)

            samples = []
            for frame_index in sample_indices:
                frame = canvas.frame_view(frame_index)
                channels = {
                    name: int(frame[channel_1_based - 1])
                    for name, channel_1_based in fixture.absolute_channels.items()
                    if 1 <= channel_1_based <= len(frame)
                }
                samples.append(
                    {
                        "frame": int(frame_index),
                        "time_s": round(frame_index / float(canvas.fps), 3),
                        "channels": channels,
                    }
                )

            song_filename = getattr(getattr(self, "current_song", None), "song_id", None) or "unknown"
            return {
                "ok": True,
                "song": song_filename,
                "fixture_id": fixture.id,
                "fps": int(canvas.fps),
                "start_time": float(start_time),
                "end_time": float(end_time),
                "start_frame": int(start_frame),
                "end_frame": int(end_frame),
                "sample_step_frames": int(step),
                "absolute_channels": dict(fixture.absolute_channels),
                "samples": samples,
            }
