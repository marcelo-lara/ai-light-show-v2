from typing import Any, Dict, Optional


def _build_prism_effects_answer_text(fixtures_result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(fixtures_result, dict) or not fixtures_result.get("ok"):
        return None
    effects: list[str] = []
    for fixture in (fixtures_result.get("data") or {}).get("fixtures") or []:
        if "prism" not in str(fixture.get("id") or "").lower():
            continue
        for effect_name in fixture.get("supported_effects") or []:
            normalized = str(effect_name or "").strip()
            if normalized and normalized not in effects:
                effects.append(normalized)
    return "Prism effects: " + ", ".join(effects) + "." if effects else None


def _build_pois_answer_text(pois_result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(pois_result, dict) or not pois_result.get("ok"):
        return None
    poi_ids = [str(poi.get("id") or "").strip() for poi in ((pois_result.get("data") or {}).get("pois") or []) if str(poi.get("id") or "").strip()]
    if not poi_ids:
        return "No POIs are available."
    return "Available POIs: " + ", ".join(poi_ids) + "."


def _build_section_count_answer_text(sections_result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(sections_result, dict) or not sections_result.get("ok"):
        return None
    return f"This song has {int(((sections_result.get('data') or {}).get('count') or 0))} sections."


def _build_chords_in_bar_answer_text(chords_result: Dict[str, Any], bar: int) -> Optional[str]:
    if not isinstance(chords_result, dict) or not chords_result.get("ok"):
        return None
    chords = (chords_result.get("data") or {}).get("chords") or []
    if not chords:
        return f"No chords were found in bar {bar}."
    parts = [f"{int(chord.get('bar', 0))}.{int(chord.get('beat', 0))} ({float(chord.get('time_s', chord.get('time', 0.0)) or 0.0):.3f}s) {str(chord.get('label') or chord.get('chord') or 'unknown')}" for chord in chords]
    return f"Bar {bar} contains: " + ", ".join(parts) + "."


def _build_cursor_section_next_beat_answer_text(cursor_result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(cursor_result, dict) or not cursor_result.get("ok"):
        return None
    payload = cursor_result.get("data") or {}
    section_name = str(payload.get("section_name") or "").strip() or "unknown section"
    if payload.get("next_bar") is None or payload.get("next_beat") is None or payload.get("next_beat_time_s") is None:
        return f"You are in {section_name}, and there is no next beat available."
    return f"You are in {section_name}, and the next beat is {int(payload.get('next_bar'))}.{int(payload.get('next_beat'))} ({float(payload.get('next_beat_time_s')):.3f}s)."


def _build_loudest_section_answer_text(section: Dict[str, Any], loudness_result: Dict[str, Any]) -> Optional[str]:
    if not section or not isinstance(loudness_result, dict) or not loudness_result.get("ok"):
        return None
    payload = loudness_result.get("data") or {}
    return f"The loudest section is {str(section.get('name') or 'unknown')} from {float(section.get('start_s', 0.0) or 0.0):.3f}s to {float(section.get('end_s', 0.0) or 0.0):.3f}s with average loudness {float(payload.get('average', 0.0)):.6f}."


def _build_first_chord_answer_text(chord_result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(chord_result, dict) or not chord_result.get("ok"):
        return None
    payload = chord_result.get("data") or {}
    chord = payload.get("chord") or {}
    label = str(chord.get("label") or chord.get("chord") or "unknown")
    bar = chord.get("bar")
    beat = chord.get("beat")
    time_s = float(chord.get("time_s", chord.get("time", 0.0)) or 0.0)
    if bar is None or beat is None:
        return f"The first occurrence of chord {label} is at {time_s:.3f}s."
    return f"The first occurrence of chord {label} is at {int(bar)}.{int(beat)} ({time_s:.3f}s)."


def _build_cursor_answer_text(cursor_result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(cursor_result, dict) or not cursor_result.get("ok"):
        return None
    payload = cursor_result.get("data") or {}
    bar = payload.get("bar")
    beat = payload.get("beat")
    time_s = float(payload.get("time_s", 0.0) or 0.0)
    section_name = str(payload.get("section_name") or "").strip()
    position_text = f"{int(bar)}.{int(beat)}" if bar is not None and beat is not None else f"{time_s:.3f}s"
    if section_name:
        return f"The cursor is at {position_text} ({time_s:.3f}s) in {section_name}."
    return f"The cursor is at {position_text} ({time_s:.3f}s)."


def _build_left_fixtures_answer_text(fixtures_result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(fixtures_result, dict) or not fixtures_result.get("ok"):
        return None
    left_ids = [str(fixture.get("id") or "").strip() for fixture in ((fixtures_result.get("data") or {}).get("fixtures") or []) if str(fixture.get("id") or "").endswith(("_l", "_pl"))]
    left_ids = [fixture_id for fixture_id in left_ids if fixture_id]
    if not left_ids:
        return "No left-side fixtures are available."
    return ", ".join(left_ids)