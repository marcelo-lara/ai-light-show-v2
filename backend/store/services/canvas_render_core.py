from typing import Any, Dict, List, Tuple

from models.chasers import ChaserDefinition, get_chaser_by_id, get_chaser_cycle_beats
from models.cues import CueEntry, CueSheet
from models.fixtures.fixture import Fixture
from services.cue_helpers.timing import beatToTimeMs


def _expand_entry_for_render(entry: CueEntry, chasers: List[ChaserDefinition], bpm: float) -> List[CueEntry]:
    if not entry.is_chaser:
        return [entry]
    if bpm <= 0.0:
        return []
    chaser = get_chaser_by_id(chasers, entry.chaser_id or "")
    if not chaser:
        return []
    try:
        repetitions = int((entry.data or {}).get("repetitions", 1))
    except (TypeError, ValueError):
        repetitions = 1
    cycle_beats = get_chaser_cycle_beats(chaser)
    expanded: List[CueEntry] = []
    for cycle in range(max(1, repetitions)):
        cycle_offset_beats = cycle * cycle_beats
        for effect in chaser.effects:
            cue_time_seconds = float(entry.time) + beatToTimeMs(cycle_offset_beats + effect.beat, bpm) / 1000.0
            duration_seconds = beatToTimeMs(effect.duration, bpm) / 1000.0
            expanded.append(
                CueEntry(
                    time=cue_time_seconds,
                    fixture_id=effect.fixture_id,
                    effect=effect.effect,
                    duration=duration_seconds,
                    data=dict(effect.data),
                    name=entry.name,
                    created_by=entry.created_by,
                )
            )
    return expanded


def iter_cues_for_render(
    cue_sheet: CueSheet | None,
    fps: int,
    chasers: List[ChaserDefinition],
    bpm: float,
) -> List[Tuple[int, int, CueEntry]]:
    if not cue_sheet:
        return []
    cues: List[Tuple[int, int, CueEntry]] = []
    for entry in cue_sheet.entries:
        for render_entry in _expand_entry_for_render(entry, chasers, bpm):
            start = int(round(float(render_entry.time) * fps))
            duration = max(0.0, float(render_entry.duration or 0.0))
            end = int(round((float(render_entry.time) + duration) * fps))
            cues.append((start, end, render_entry))
    cues.sort(key=lambda item: (item[0], item[2].fixture_id or "", item[2].effect or ""))
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
