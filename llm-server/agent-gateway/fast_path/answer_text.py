from typing import Any, Dict, Optional


def _effect_id(effect: Any) -> str:
    if isinstance(effect, dict):
        return str(effect.get("id") or "").strip()
    return str(effect or "").strip()


def _format_bar_beat(bar: Any, beat: Any) -> Optional[str]:
    if bar is None or beat is None:
        return None
    try:
        bar_value = int(bar)
        beat_value = int(beat)
    except (TypeError, ValueError):
        return None
    if bar_value <= 0 or beat_value <= 0:
        return None
    return f"{bar_value}.{beat_value}"


def _build_prism_effects_answer_text(fixtures_result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(fixtures_result, dict) or not fixtures_result.get("ok"):
        return None
    effects: list[str] = []
    for fixture in (fixtures_result.get("data") or {}).get("fixtures") or []:
        if "prism" not in str(fixture.get("id") or "").lower():
            continue
        for effect_name in fixture.get("supported_effects") or []:
            normalized = _effect_id(effect_name)
            if normalized and normalized not in effects:
                effects.append(normalized)
    return "Prism effects: " + ", ".join(effects) + "." if effects else None


def _build_fixture_type_count_answer_text(fixtures_result: Dict[str, Any], fixture_type: str, label: str) -> Optional[str]:
    if not isinstance(fixtures_result, dict) or not fixtures_result.get("ok"):
        return None
    fixture_ids = [
        str(fixture.get("id") or "").strip()
        for fixture in ((fixtures_result.get("data") or {}).get("fixtures") or [])
        if str(fixture.get("type") or "").strip().lower() == fixture_type and str(fixture.get("id") or "").strip()
    ]
    if not fixture_ids:
        return f"This rig has no {label}."
    return f"This rig has {len(fixture_ids)} {label}: " + ", ".join(fixture_ids) + "."


def _build_fixture_effects_answer_text(fixtures_result: Dict[str, Any], fixture_ids: list[str], label: str) -> Optional[str]:
    if not isinstance(fixtures_result, dict) or not fixtures_result.get("ok"):
        return None
    if not fixture_ids:
        return None
    fixtures = {
        str(fixture.get("id") or "").strip(): fixture
        for fixture in ((fixtures_result.get("data") or {}).get("fixtures") or [])
        if isinstance(fixture, dict) and str(fixture.get("id") or "").strip()
    }
    matched_fixtures = [fixtures[fixture_id] for fixture_id in fixture_ids if fixture_id in fixtures]
    if not matched_fixtures:
        return None
    effects: list[str] = []
    for fixture in matched_fixtures:
        for effect_name in fixture.get("supported_effects") or []:
            normalized = _effect_id(effect_name)
            if normalized and normalized not in effects:
                effects.append(normalized)
    if not effects:
        return None
    if len(matched_fixtures) == 1:
        fixture_id = str(matched_fixtures[0].get("id") or label).strip()
        return f"{fixture_id} effects: " + ", ".join(effects) + "."
    return f"{label} effects: " + ", ".join(effects) + "."


def _build_fixture_type_list_answer_text(fixtures_result: Dict[str, Any], fixture_type: str, label: str) -> Optional[str]:
    if not isinstance(fixtures_result, dict) or not fixtures_result.get("ok"):
        return None
    fixture_ids = [
        str(fixture.get("id") or "").strip()
        for fixture in ((fixtures_result.get("data") or {}).get("fixtures") or [])
        if str(fixture.get("type") or "").strip().lower() == fixture_type and str(fixture.get("id") or "").strip()
    ]
    if not fixture_ids:
        return f"No {label} are available."
    return f"{label.capitalize()}: " + ", ".join(fixture_ids) + "."


def _build_missing_fixture_type_qualifier_answer_text(fixtures_result: Dict[str, Any], fixture_type: str, qualifier: str, singular_label: str, plural_label: str) -> Optional[str]:
    if not isinstance(fixtures_result, dict) or not fixtures_result.get("ok"):
        return None
    available_ids = [
        str(fixture.get("id") or "").strip()
        for fixture in ((fixtures_result.get("data") or {}).get("fixtures") or [])
        if str(fixture.get("type") or "").strip().lower() == fixture_type and str(fixture.get("id") or "").strip()
    ]
    if not available_ids:
        return f"We do not have any {plural_label}."
    return f"We do not have a {qualifier} {singular_label}. Available {plural_label}: " + ", ".join(available_ids) + "."


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
    section_name = str(payload.get("section_name") or "").strip()
    next_section_name = str(payload.get("next_section_name") or "").strip()
    if section_name:
        section_text = f"in {section_name}"
    elif next_section_name:
        section_text = f"before {next_section_name}"
    else:
        section_text = "between sections"
    if payload.get("next_bar") is None or payload.get("next_beat") is None or payload.get("next_beat_time_s") is None:
        return f"You are {section_text}, and there is no next beat available."
    next_position = _format_bar_beat(payload.get("next_bar"), payload.get("next_beat"))
    if next_position is not None:
        return f"You are {section_text}, and the next beat is {next_position} ({float(payload.get('next_beat_time_s')):.3f}s)."
    return f"You are {section_text}, and the next beat is at {float(payload.get('next_beat_time_s')):.3f}s."


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
    time_s = float(payload.get("time_s", 0.0) or 0.0)
    section_name = str(payload.get("section_name") or "").strip()
    next_section_name = str(payload.get("next_section_name") or "").strip()
    position_text = _format_bar_beat(payload.get("bar"), payload.get("beat")) or f"{time_s:.3f}s"
    if section_name:
        return f"The cursor is at {position_text} ({time_s:.3f}s) in {section_name}."
    if next_section_name:
        return f"The cursor is at {time_s:.3f}s before {next_section_name}."
    return f"The cursor is at {position_text} ({time_s:.3f}s)."


def _build_left_fixtures_answer_text(fixtures_result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(fixtures_result, dict) or not fixtures_result.get("ok"):
        return None
    left_ids = [str(fixture.get("id") or "").strip() for fixture in ((fixtures_result.get("data") or {}).get("fixtures") or []) if str(fixture.get("id") or "").endswith(("_l", "_pl"))]
    left_ids = [fixture_id for fixture_id in left_ids if fixture_id]
    if not left_ids:
        return "No left-side fixtures are available."
    return ", ".join(left_ids)