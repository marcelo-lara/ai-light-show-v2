from __future__ import annotations

from typing import Any, Dict, List

from api.intents.llm.timing_context import build_section_by_name_payload
from store.services.canvas_render_core import _expand_entry_for_render


def build_cue_window_payload(manager, start_s: float, end_s: float) -> Dict[str, Any]:
    state_manager = manager.state_manager
    cue_sheet = getattr(state_manager, "cue_sheet", None)
    entries = list(getattr(cue_sheet, "entries", []) or [])
    song_meta = getattr(getattr(state_manager, "current_song", None), "meta", None)
    bpm = float(getattr(song_meta, "bpm", 0.0) or 0.0)
    chasers = list(getattr(state_manager, "chasers", []) or [])

    raw_entries = []
    expanded_entries = []
    for entry in entries:
        entry_time = float(entry.time)
        entry_duration = max(0.0, float(entry.duration or 0.0))
        entry_end = entry_time + entry_duration
        if entry_duration > 0.0:
            overlaps = entry_time < end_s and entry_end > start_s
        else:
            overlaps = start_s <= entry_time <= end_s
        if not overlaps:
            continue

        raw_entries.append(entry.model_dump(exclude_none=True))
        for expanded in _expand_entry_for_render(entry, chasers, bpm):
            expanded_time = float(expanded.time)
            expanded_duration = max(0.0, float(expanded.duration or 0.0))
            expanded_end = expanded_time + expanded_duration
            if expanded_duration > 0.0:
                expanded_overlaps = expanded_time < end_s and expanded_end > start_s
            else:
                expanded_overlaps = start_s <= expanded_time <= end_s
            if not expanded_overlaps:
                continue

            payload = expanded.model_dump(exclude_none=True)
            if entry.is_chaser:
                payload["source_chaser"] = entry.chaser_id
            expanded_entries.append(payload)

    fixtures_used = sorted({str(entry.get("fixture_id") or "") for entry in expanded_entries if entry.get("fixture_id")})
    effects_used = sorted({str(entry.get("effect") or "") for entry in expanded_entries if entry.get("effect")})
    if effects_used:
        effect_text = ", ".join(effects_used)
        answer = f"The effects rendered from {start_s:g} to {end_s:g} seconds are: {effect_text}."
    else:
        answer = f"No effects are rendered from {start_s:g} to {end_s:g} seconds."
    return {
        "start_s": start_s,
        "end_s": end_s,
        "raw_entries": raw_entries,
        "expanded_entries": expanded_entries,
        "fixtures_used": fixtures_used,
        "effects_used": effects_used,
        "answer": answer,
    }


def build_cue_section_payload(manager, section_name: str) -> Dict[str, Any] | None:
    section = build_section_by_name_payload(manager, section_name)
    if section is None:
        return None
    payload = {
        "section": section,
        **build_cue_window_payload(manager, float(section["start_s"]), float(section["end_s"])),
    }
    fixtures_used = payload.get("fixtures_used") or []
    if fixtures_used:
        fixture_text = ", ".join(str(fixture_id) for fixture_id in fixtures_used)
        payload["answer"] = f"The fixtures used in the {section['name']} section are: {fixture_text}."
    else:
        payload["answer"] = f"No fixtures are used in the {section['name']} section."
    return payload