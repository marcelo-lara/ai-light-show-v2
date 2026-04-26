from typing import Any, Dict, List, Tuple

from models.chasers import ChaserDefinition, get_chaser_by_id, get_chaser_cycle_beats
from models.cues import CueEntry, CueSheet
from models.fixtures.fixture import Fixture
from models.fixtures.moving_heads.orbit_helpers import orbit_writes_dimmer
from models.fixtures.moving_heads.poi_geometry import estimate_circle_pan_tilt
from models.fixtures.moving_heads.travel_helpers import EFFECT_SAFETY_PREROLL_SECONDS, EFFECT_SETTLE_SECONDS, fixture_travel_profile_seconds
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

    if chaser.type == "dynamic" and chaser.generator_id:
        from services.dynamic_chasers import GENERATORS
        from models.chasers import ChaserEffect as _ChaserEffect
        generator = GENERATORS.get(chaser.generator_id)
        if not generator:
            return []
        # Per-cue data may override default_params (excluding bookkeeping keys)
        merged_params = dict(chaser.default_params)
        override = {k: v for k, v in (entry.data or {}).items() if k != "repetitions"}
        merged_params.update(override)
        source_effects = [_ChaserEffect(**e) for e in generator(merged_params)]
    else:
        source_effects = chaser.effects

    cycle_beats = get_chaser_cycle_beats(chaser)
    expanded: List[CueEntry] = []
    for cycle in range(max(1, repetitions)):
        cycle_offset_beats = cycle * cycle_beats
        for effect in source_effects:
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


def _fixture_axis_position_from_current_values(fixture: Fixture) -> tuple[int, int] | None:
    current_values = fixture.current_values or {}
    pan = current_values.get("pan")
    tilt = current_values.get("tilt")
    if pan is None or tilt is None:
        if hasattr(fixture, "_has_axis_16bit") and fixture._has_axis_16bit("pan") and fixture._has_axis_16bit("tilt"):
            return 0, 0
        return None
    try:
        return int(pan), int(tilt)
    except (TypeError, ValueError):
        return None


def _estimate_sweep_end_position(fixture: Fixture, data: dict[str, Any]) -> tuple[int, int] | None:
    subject_poi = str(data.get("subject_POI") or "").strip()
    start_poi = str(data.get("start_POI") or "").strip()
    if not subject_poi or not start_poi:
        return None

    subject_pan, subject_tilt = fixture._resolve_poi_pan_tilt_u16(subject_poi)
    start_pan, start_tilt = fixture._resolve_poi_pan_tilt_u16(start_poi)
    if subject_pan is None or subject_tilt is None or start_pan is None or start_tilt is None:
        return None

    end_poi = str(data.get("end_POI") or "").strip()
    if end_poi:
        end_pan, end_tilt = fixture._resolve_poi_pan_tilt_u16(end_poi)
        if end_pan is not None and end_tilt is not None:
            return int(end_pan), int(end_tilt)

    return (
        fixture._clamp_u16((2 * int(subject_pan)) - int(start_pan)),
        fixture._clamp_u16((2 * int(subject_tilt)) - int(start_tilt)),
    )


def _estimate_orbit_end_position(fixture: Fixture, data: dict[str, Any]) -> tuple[int, int] | None:
    subject_poi = str(data.get("subject_POI") or "").strip()
    start_poi = str(data.get("start_POI") or "").strip()
    if not subject_poi or not start_poi:
        return None

    subject_pan, subject_tilt = fixture._resolve_poi_pan_tilt_u16(subject_poi)
    if subject_pan is None or subject_tilt is None:
        return None
    return int(subject_pan), int(subject_tilt)


def _estimate_circle_end_position(fixture: Fixture, data: dict[str, Any]) -> tuple[int, int] | None:
    pan_u16, tilt_u16 = estimate_circle_pan_tilt(fixture, data, 1.0)
    if pan_u16 is None or tilt_u16 is None:
        return None
    return int(pan_u16), int(tilt_u16)


def _estimate_entry_end_position(fixture: Fixture, entry: CueEntry) -> tuple[int, int] | None:
    data = entry.data or {}
    effect = str(entry.effect or "").strip().lower()
    if effect == "move_to":
        target = fixture._parse_pan_tilt_targets_u16(data)
        if target[0] is None or target[1] is None:
            return None
        return int(target[0]), int(target[1])
    if effect == "circle":
        return _estimate_circle_end_position(fixture, data)
    if effect == "orbit":
        return _estimate_orbit_end_position(fixture, data)
    if effect == "orbit_out":
        start_poi = str(data.get("start_POI") or "").strip()
        if not start_poi:
            return None
        start_pan, start_tilt = fixture._resolve_poi_pan_tilt_u16(start_poi)
        if start_pan is None or start_tilt is None:
            return None
        return int(start_pan), int(start_tilt)
    if effect == "move_to_poi":
        target_poi = str(data.get("target_POI") or data.get("poi") or data.get("POI") or "").strip()
        if not target_poi:
            return None
        target_pan, target_tilt = fixture._resolve_poi_pan_tilt_u16(target_poi)
        if target_pan is None or target_tilt is None:
            return None
        return int(target_pan), int(target_tilt)
    if effect == "sweep":
        return _estimate_sweep_end_position(fixture, data)
    return None


def _estimate_sweep_preroll_seconds(fixture: Fixture, data: dict[str, Any], last_position: tuple[int, int] | None) -> float:
    start_poi = str(data.get("start_POI") or "").strip()
    if not start_poi or last_position is None:
        return 0.0

    start_pan, start_tilt = fixture._resolve_poi_pan_tilt_u16(start_poi)
    if start_pan is None or start_tilt is None:
        return 0.0

    last_pan, last_tilt = last_position
    pan_full_travel_seconds, tilt_full_travel_seconds = fixture_travel_profile_seconds(fixture)
    pan_seconds = (abs(int(start_pan) - int(last_pan)) / 65535.0) * pan_full_travel_seconds
    tilt_seconds = (abs(int(start_tilt) - int(last_tilt)) / 65535.0) * tilt_full_travel_seconds
    return max(0.0, pan_seconds, tilt_seconds) + EFFECT_SAFETY_PREROLL_SECONDS + EFFECT_SETTLE_SECONDS


def _estimate_orbit_preroll_seconds(fixture: Fixture, data: dict[str, Any], last_position: tuple[int, int] | None) -> float:
    if not orbit_writes_dimmer(data):
        return 0.0
    start_poi = str(data.get("start_POI") or "").strip()
    if not start_poi or last_position is None:
        return 0.0

    start_pan, start_tilt = fixture._resolve_poi_pan_tilt_u16(start_poi)
    if start_pan is None or start_tilt is None:
        return 0.0

    last_pan, last_tilt = last_position
    pan_full_travel_seconds, tilt_full_travel_seconds = fixture_travel_profile_seconds(fixture)
    pan_seconds = (abs(int(start_pan) - int(last_pan)) / 65535.0) * pan_full_travel_seconds
    tilt_seconds = (abs(int(start_tilt) - int(last_tilt)) / 65535.0) * tilt_full_travel_seconds
    return max(0.0, pan_seconds, tilt_seconds) + EFFECT_SAFETY_PREROLL_SECONDS + EFFECT_SETTLE_SECONDS


def _estimate_orbit_out_preroll_seconds(fixture: Fixture, data: dict[str, Any], last_position: tuple[int, int] | None) -> float:
    if not orbit_writes_dimmer(data):
        return 0.0
    subject_poi = str(data.get("subject_POI") or "").strip()
    if not subject_poi or last_position is None:
        return 0.0

    subject_pan, subject_tilt = fixture._resolve_poi_pan_tilt_u16(subject_poi)
    if subject_pan is None or subject_tilt is None:
        return 0.0

    last_pan, last_tilt = last_position
    pan_full_travel_seconds, tilt_full_travel_seconds = fixture_travel_profile_seconds(fixture)
    pan_seconds = (abs(int(subject_pan) - int(last_pan)) / 65535.0) * pan_full_travel_seconds
    tilt_seconds = (abs(int(subject_tilt) - int(last_tilt)) / 65535.0) * tilt_full_travel_seconds
    return max(0.0, pan_seconds, tilt_seconds) + EFFECT_SAFETY_PREROLL_SECONDS + EFFECT_SETTLE_SECONDS


def estimate_sweep_preroll_seconds(fixture: Fixture, data: dict[str, Any], last_position: tuple[int, int] | None) -> float:
    return _estimate_sweep_preroll_seconds(fixture, data, last_position)


def estimate_orbit_preroll_seconds(fixture: Fixture, data: dict[str, Any], last_position: tuple[int, int] | None) -> float:
    return _estimate_orbit_preroll_seconds(fixture, data, last_position)


def estimate_orbit_out_preroll_seconds(fixture: Fixture, data: dict[str, Any], last_position: tuple[int, int] | None) -> float:
    return _estimate_orbit_out_preroll_seconds(fixture, data, last_position)


def iter_cues_for_render(
    cue_sheet: CueSheet | None,
    fixtures: List[Fixture],
    fps: int,
    chasers: List[ChaserDefinition],
    bpm: float,
) -> List[Tuple[int, int, CueEntry]]:
    if not cue_sheet:
        return []
    cues: List[Tuple[int, int, CueEntry]] = []
    fixture_map = {fixture.id: fixture for fixture in fixtures}
    fixture_positions: Dict[str, tuple[int, int]] = {}
    for entry in cue_sheet.entries:
        for render_entry in _expand_entry_for_render(entry, chasers, bpm):
            render_data = dict(render_entry.data or {})
            start = int(round(float(render_entry.time) * fps))
            duration = max(0.0, float(render_entry.duration or 0.0))
            end = int(round((float(render_entry.time) + duration) * fps))
            fixture = fixture_map.get(render_entry.fixture_id or "")
            if fixture and str(render_entry.effect or "").strip().lower() in {"sweep", "orbit", "orbit_out"}:
                last_position = fixture_positions.get(fixture.id) or _fixture_axis_position_from_current_values(fixture)
                effect_name = str(render_entry.effect or "").strip().lower()
                if effect_name == "sweep":
                    preroll_seconds = _estimate_sweep_preroll_seconds(fixture, render_data, last_position)
                elif effect_name == "orbit_out":
                    preroll_seconds = _estimate_orbit_out_preroll_seconds(fixture, render_data, last_position)
                else:
                    preroll_seconds = _estimate_orbit_preroll_seconds(fixture, render_data, last_position)
                preroll_frames = max(0, int(round(preroll_seconds * fps)))
                if preroll_frames > 0:
                    preroll_key = "__sweep_preroll_frames" if effect_name == "sweep" else "__orbit_preroll_frames"
                    render_data[preroll_key] = preroll_frames
                    start = max(0, start - preroll_frames)
                    render_entry = CueEntry(
                        time=render_entry.time,
                        fixture_id=render_entry.fixture_id,
                        effect=render_entry.effect,
                        duration=render_entry.duration,
                        data=render_data,
                        name=render_entry.name,
                        created_by=render_entry.created_by,
                    )
            cues.append((start, end, render_entry))

            if fixture:
                end_position = _estimate_entry_end_position(fixture, render_entry)
                if end_position is not None:
                    fixture_positions[fixture.id] = end_position
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
