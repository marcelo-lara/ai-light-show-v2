from __future__ import annotations

from typing import Any

from models.song import build_song_analysis
from models.song.analysis_loader import collect_missing_analysis_artifacts
from services.cue_helpers.song_draft.fixture_roles import resolve_fixture_roles, select_orbit_pair
from services.cue_helpers.song_draft.patterns import accent_times, beat_duration_s, section_palette


def generate_song_draft(song, fixtures: list[Any], pois: list[dict[str, Any]], supported_effects) -> list[dict[str, Any]]:
    analysis = build_song_analysis(song)
    if not analysis.beats_available:
        raise ValueError("beats_unavailable")
    if not analysis.sections_available:
        raise ValueError("sections_unavailable")
    if not analysis.features_available:
        error = ValueError("features_unavailable")
        setattr(error, "missing_artifacts", collect_missing_analysis_artifacts(song))
        raise error
    roles = resolve_fixture_roles(fixtures, pois, supported_effects)
    entries = [{"time": 0.0, "fixture_id": fixture_id, "effect": "blackout", "duration": 0.0, "data": {}} for fixture_id in roles["pars"] + roles["movers"]]
    for section in analysis.sections:
        section_beats = [beat for beat in analysis.beats if section.start_s <= float(beat.time) < section.end_s]
        if not section_beats:
            continue
        entries.extend(generate_par_section(section, section_beats, roles["pars"], analysis.bpm))
        entries.extend(generate_motion_section(section, section_beats, roles))
    return entries


def generate_par_section(section, section_beats, par_ids: list[str], bpm: float) -> list[dict[str, Any]]:
    color, flash_color = section_palette(section)
    duration_s = beat_duration_s(section_beats, bpm)
    entries: list[dict[str, Any]] = []
    walk_index = 0
    active_fixture = None
    for beat in section_beats:
        cue_time = float(beat.time)
        if int(beat.beat) == 1:
            entries.extend({"time": cue_time, "fixture_id": fixture_id, "effect": "flash", "duration": max(0.15, duration_s * 0.75), "data": {"color": flash_color}} for fixture_id in par_ids)
            continue
        fixture_id = par_ids[walk_index % len(par_ids)]
        walk_index += 1
        if active_fixture and active_fixture != fixture_id:
            entries.append({"time": cue_time, "fixture_id": active_fixture, "effect": "blackout", "duration": 0.0, "data": {}})
        entries.append({"time": cue_time, "fixture_id": fixture_id, "effect": "full", "duration": 0.0, "data": dict(color)})
        active_fixture = fixture_id
    for window in section.low_windows:
        entries.extend({"time": float(window.start_s), "fixture_id": fixture_id, "effect": "fade_out", "duration": max(0.1, float(window.end_s) - float(window.start_s)), "data": {}} for fixture_id in par_ids)
    return entries


def generate_motion_section(section, section_beats, roles: dict[str, Any]) -> list[dict[str, Any]]:
    duration_s = beat_duration_s(section_beats, 0.0)
    phrase_beats = [beat for beat in section_beats if int(beat.beat) == 1][::2]
    entries: list[dict[str, Any]] = []
    orbiters = roles["orbiters"][:2]
    for index, fixture_id in enumerate(orbiters):
        pair = select_orbit_pair(fixture_id, roles["poi_by_fixture"])
        if pair is None:
            continue
        for beat in phrase_beats[index:: max(1, len(orbiters))]:
            entries.append({"time": float(beat.time), "fixture_id": fixture_id, "effect": "full", "duration": 0.0, "data": {}})
            entries.append({"time": float(beat.time), "fixture_id": fixture_id, "effect": "orbit", "duration": max(duration_s * 4.0, 0.5), "data": {"start_POI": pair[0], "subject_POI": pair[1], "orbits": 1.0}})
    accents = accent_times(section, ("vocals", "drums"))
    movers = orbiters or roles["movers"][:2]
    for index, time_s in enumerate(accents):
        if not movers:
            break
        fixture_id = movers[index % len(movers)]
        entries.append({"time": float(time_s), "fixture_id": fixture_id, "effect": "flash", "duration": max(duration_s * 0.75, 0.2), "data": {}})
    return entries