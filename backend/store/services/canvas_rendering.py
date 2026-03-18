import math
from typing import Any, Callable, Dict, List, Tuple

from models.chasers import ChaserDefinition
from models.cues import CueEntry, CueSheet
from models.fixtures.fixture import Fixture
from store.dmx_canvas import DMX_CHANNELS, DMXCanvas
from store.services.canvas_debug import dump_canvas_debug
from store.services.canvas_render_core import iter_cues_for_render, render_entry_into_universe


def render_cue_sheet_to_canvas(
    *,
    fixtures: List[Fixture],
    cue_sheet: CueSheet | None,
    chasers: List[ChaserDefinition],
    bpm: float,
    song_length_seconds: float,
    fps: int,
    apply_arm: Callable[[bytearray], None],
) -> DMXCanvas:
    total_frames = max(1, int(math.ceil(song_length_seconds * fps)) + 1)
    canvas = DMXCanvas.allocate(fps=fps, total_frames=total_frames)

    base_universe = bytearray(DMX_CHANNELS)
    apply_arm(base_universe)

    cues = iter_cues_for_render(cue_sheet, fps, chasers, bpm)
    cues_by_start: Dict[int, List[Tuple[int, int, CueEntry]]] = {}
    for start, end, entry in cues:
        cues_by_start.setdefault(start, []).append((start, end, entry))

    active: List[Tuple[int, int, CueEntry]] = []
    universe = bytearray(base_universe)
    entry_render_state: Dict[int, Dict[str, Any]] = {}

    for frame_index in range(total_frames):
        if frame_index in cues_by_start:
            active.extend(cues_by_start[frame_index])

        if active:
            active = [(start, end, entry) for (start, end, entry) in active if end >= frame_index]

        if active:
            active_sorted = sorted(active, key=lambda item: (item[2].time, item[2].fixture_id or "", item[2].effect or ""))
            for start_frame, end_frame, entry in active_sorted:
                render_entry_into_universe(
                    fixtures=fixtures,
                    universe=universe,
                    frame_index=frame_index,
                    start_frame=start_frame,
                    end_frame=end_frame,
                    entry=entry,
                    entry_render_state=entry_render_state,
                    fps=fps,
                )

        canvas.set_frame(frame_index, universe)

    return canvas


def render_preview_canvas(
    *,
    fixture: Fixture,
    effect: str,
    duration: float,
    data: Dict[str, Any],
    base_universe: bytearray,
    fps: int,
) -> DMXCanvas:
    total_frames = max(1, int(math.ceil(float(duration) * fps)) + 1)
    canvas = DMXCanvas.allocate(fps=fps, total_frames=total_frames)
    universe = bytearray(base_universe)
    render_state: Dict[str, Any] = {}

    end_frame = total_frames - 1
    for frame_index in range(total_frames):
        fixture.render_effect(
            universe,
            effect=effect,
            frame_index=frame_index,
            start_frame=0,
            end_frame=end_frame,
            fps=fps,
            data=data,
            render_state=render_state,
        )
        canvas.set_frame(frame_index, universe)

    return canvas
