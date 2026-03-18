# pyright: reportAttributeAccessIssue=false

from typing import Any, Dict

from models.fixtures.fixture import Fixture
from store.dmx_canvas import DMXCanvas
from store.services.canvas_rendering import (
    dump_canvas_debug,
    render_cue_sheet_to_canvas,
    render_preview_canvas,
)

from ..constants import FPS


class StateCoreRenderMixin:
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
