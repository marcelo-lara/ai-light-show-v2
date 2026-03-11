from typing import Any, Dict, List, Tuple

from models.cue import CueEntry, CueSheet
from models.fixture import Fixture


def iter_cues_for_render(cue_sheet: CueSheet | None, fps: int) -> List[Tuple[int, int, CueEntry]]:
    if not cue_sheet:
        return []
    cues: List[Tuple[int, int, CueEntry]] = []
    for entry in cue_sheet.entries:
        start = int(round(float(entry.time) * fps))
        duration = max(0.0, float(entry.duration or 0.0))
        end = int(round((float(entry.time) + duration) * fps))
        cues.append((start, end, entry))
    cues.sort(key=lambda item: (item[0], item[2].fixture_id, item[2].effect))
    return cues


def render_entry_into_universe(
    fixtures: List[Fixture],
    universe: bytearray,
    frame_index: int,
    start_frame: int,
    end_frame: int,
    entry: CueEntry,
    entry_render_state: Dict[int, Dict[str, Any]],
    fps: int,
) -> None:
    fixture = next((f for f in fixtures if f.id == entry.fixture_id), None)
    if not fixture:
        return

    state_key = id(entry)
    render_state = entry_render_state.setdefault(state_key, {})
    fixture.render_effect(
        universe,
        effect=entry.effect,
        frame_index=frame_index,
        start_frame=start_frame,
        end_frame=end_frame,
        fps=fps,
        data=entry.data or {},
        render_state=render_state,
    )
