from typing import Any, Dict

import orjson


def _effect_id(effect: Any) -> str:
    if isinstance(effect, dict):
        return str(effect.get("id") or "").strip()
    return str(effect or "").strip()


def _format_effects(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    if not payload:
        return _format_generic_result(result)
    effects = payload.get("effects") or {}
    lines = ["Effects:"]
    for effect_id, effect in sorted(effects.items()):
        if not isinstance(effect, dict):
            continue
        tags = ",".join(effect.get("tags") or [])
        lines.append(f"- id={effect_id} name={effect.get('name')} tags={tags} description={effect.get('description')}")
    return "\n".join(lines) if len(lines) > 1 else "Effects: unavailable"


def _format_sections(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    sections = payload.get("sections") or []
    song = payload.get("song") or "unknown"
    if not sections:
        return f"Song: {song}\nSections: unavailable"
    lines = [f"Song: {song}", "Sections:"]
    for section in sections:
        lines.append(
            f"- {section.get('name') or 'Unnamed'}: start={float(section.get('start_s', 0.0)):.3f}s ({section.get('start_bar')}.{section.get('start_beat')}) end={float(section.get('end_s', 0.0)):.3f}s ({section.get('end_bar')}.{section.get('end_beat')})"
        )
    return "\n".join(lines)


def _format_section_match(result: Dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return _format_generic_result(result)
    if not result.get("ok"):
        error = result.get("error") or {}
        return "SECTION_LOOKUP_RESULT\nsection_found=false\n" f"error_code={error.get('code', 'unknown')}\nerror_message={error.get('message', 'unknown')}"
    payload = result.get("data") or {}
    section = payload.get("section") or {}
    return (
        "SECTION_LOOKUP_RESULT\nsection_found=true\n"
        f"song={payload.get('song', 'unknown')}\nsection_name={section.get('name', 'Unnamed')}\n"
        f"section_start_seconds={float(section.get('start_s', 0.0)):.3f}\nsection_end_seconds={float(section.get('end_s', 0.0)):.3f}"
    )


def _format_beats(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    beats = payload.get("beats") or []
    song = payload.get("song") or "unknown"
    if not beats:
        return f"Song: {song}\nBeats: unavailable"
    lines = [f"Song: {song}", "Beats:"]
    for beat in beats[:32]:
        lines.append(f"- time={float(beat.get('time', 0.0)):.3f}s bar={int(beat.get('bar', 0))} beat={int(beat.get('beat', 0))}")
    return "\n".join(lines)


def _format_bar_beat_match(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    position = payload.get("position") or {}
    if not position:
        return _format_generic_result(result)
    return f"Song: {payload.get('song', 'unknown')}\nPosition:\n- time={float(position.get('time', 0.0)):.3f}s bar={int(position.get('bar', 0))} beat={int(position.get('beat', 0))} chord={position.get('chord', 'unknown')}"


def _format_chord_match(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    chord = payload.get("chord") or {}
    if not chord:
        return _format_generic_result(result)
    return f"Song: {payload.get('song', 'unknown')}\nChord Match:\n- occurrence={int(payload.get('occurrence', 1))} time={float(chord.get('time_s', 0.0)):.3f}s bar={int(chord.get('bar', 0))} beat={int(chord.get('beat', 0))} chord={chord.get('label', 'unknown')}"


def _format_chords(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    chords = payload.get("chords") or []
    song = payload.get("song") or "unknown"
    if not chords:
        return f"Song: {song}\nChords: unavailable"
    lines = [f"Song: {song}", "Chords:"]
    for chord in chords[:32]:
        lines.append(f"- time={float(chord.get('time_s', 0.0)):.3f}s bar={int(chord.get('bar', 0))} beat={int(chord.get('beat', 0))} chord={chord.get('label', 'unknown')}")
    return "\n".join(lines)


def _format_cue_window(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    entries = payload.get("entries") or []
    lines = [f"Cue Window: start={float(payload.get('start_time', 0.0)):.3f}s end={float(payload.get('end_time', 0.0)):.3f}s", "Entries:" if entries else "Entries: none"]
    for entry in entries[:64]:
        if entry.get("chaser_id"):
            lines.append(f"- time={float(entry.get('time', 0.0)):.3f}s chaser={entry.get('chaser_id')} created_by={entry.get('created_by', 'unknown')}")
        else:
            lines.append(f"- time={float(entry.get('time', 0.0)):.3f}s fixture={entry.get('fixture_id')} effect={entry.get('effect')} duration={float(entry.get('duration', 0.0)):.3f}s created_by={entry.get('created_by', 'unknown')}")
    return "\n".join(lines)


def _format_fixtures(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    fixtures = payload.get("fixtures") or []
    if not fixtures:
        return "Fixtures: unavailable"
    lines = ["Fixtures:"]
    for fixture in fixtures[:64]:
        effect_ids = [_effect_id(effect) for effect in fixture.get("supported_effects") or []]
        lines.append(
            f"- id={fixture.get('id')} name={fixture.get('name')} type={fixture.get('type')} "
            f"supports_move_to_poi={'move_to_poi' in effect_ids} supported_effects={','.join(effect_ids)}"
        )
    return "\n".join(lines)


def _format_pois(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    pois = payload.get("pois") or []
    if not pois:
        return "POIs: unavailable"
    return "\n".join([
        "POIs:",
        "Use POI ids as data.target_POI in move_to_poi proposals and as data.start_POI, data.subject_POI, and data.end_POI in orbit or sweep proposals.",
    ] + [f"- id={poi.get('id')} name={poi.get('name')}" for poi in pois[:64]])


def _format_chasers(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    chasers = payload.get("chasers") or []
    if not chasers:
        return "Chasers: unavailable"
    return "\n".join(["Chasers:"] + [f"- id={chaser.get('id')} name={chaser.get('name')} description={chaser.get('description')}" for chaser in chasers[:32]])


def _format_cursor(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    if not payload:
        return _format_generic_result(result)
    return f"Cursor: proposal_time={float(payload.get('time_s', 0.0)):.3f}s bar={payload.get('bar')} beat={payload.get('beat')} section={payload.get('section_name')} next={payload.get('next_bar')}.{payload.get('next_beat')}@{payload.get('next_beat_time_s')}s"


def _format_loudness(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    if not payload:
        return orjson.dumps(result).decode("utf-8")
    return f"Song: {payload.get('song', 'unknown')}\nWindow: start={float(payload.get('start_time', 0.0)):.3f}s end={float(payload.get('end_time', 0.0) or 0.0):.3f}s\nLoudness: avg={float(payload.get('average', 0.0)):.6f} min={float(payload.get('minimum', 0.0)):.6f} max={float(payload.get('maximum', 0.0)):.6f} samples={int(payload.get('samples', 0))}"


def _format_generic_result(result: Any) -> str:
    return orjson.dumps(result).decode("utf-8")


def _render_tool_result(tool_name: str, result: Any) -> str:
    if not isinstance(result, dict) or not result.get("ok"):
        return _format_generic_result(result)
    if tool_name == "mcp_read_sections":
        return _format_sections(result)
    if tool_name == "mcp_find_section":
        return _format_section_match(result)
    if tool_name in {"mcp_read_beats", "mcp_read_bar_beats"}:
        return _format_beats(result)
    if tool_name == "mcp_find_bar_beat":
        return _format_bar_beat_match(result)
    if tool_name == "mcp_find_chord":
        return _format_chord_match(result)
    if tool_name == "mcp_read_chords":
        return _format_chords(result)
    if tool_name == "mcp_read_cue_window":
        return _format_cue_window(result)
    if tool_name == "mcp_read_fixtures":
        return _format_fixtures(result)
    if tool_name == "mcp_read_effects":
        return _format_effects(result)
    if tool_name == "mcp_read_pois":
        return _format_pois(result)
    if tool_name == "mcp_read_chasers":
        return _format_chasers(result)
    if tool_name == "mcp_read_cursor":
        return _format_cursor(result)
    if tool_name == "mcp_read_loudness":
        return _format_loudness(result)
    return _format_generic_result(result)