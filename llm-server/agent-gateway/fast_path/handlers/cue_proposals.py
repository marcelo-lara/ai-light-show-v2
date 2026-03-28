from typing import Any, Dict, List, Optional

from fast_path.extractors.chords import _extract_chord_label, _extract_chord_transition, _find_chord_spans, _find_chord_times, _find_chord_transition_time
from fast_path.extractors.effects import _color_name_to_rgb, _extract_color_name, _extract_effect_name
from fast_path.extractors.fixtures import _resolve_fixture_ids_from_prompt, _resolve_non_parcan_fixture_ids, _resolve_parcan_fixture_ids, _resolve_prism_fixture_ids, _resolve_proton_fixture_ids
from fast_path.extractors.sections import _extract_section_reference, _section_start_times
from fast_path.extractors.timing import _estimate_beat_seconds, _extract_beat_duration, _extract_time_seconds
from fast_path.proposals import _proposal_for_tool
from gateway_mcp.client import call_mcp


def _is_full_cue_clear_request(prompt: str) -> bool:
    lowered = str(prompt or "").lower()
    return bool("clear the cue" in lowered or ("cue" in lowered and any(token in lowered for token in ["all", "entire", "whole", "full"])))


async def try_cue_proposals_fast_path(prompt: str, lowered: str) -> Optional[Dict[str, Any]]:
    section_name, _section_occurrence = _extract_section_reference(prompt)
    used_tools: List[str] = []
    cue_time = _extract_time_seconds(prompt)
    if cue_time is not None and "flash" in lowered:
        used_tools.append("mcp_read_fixtures")
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        fixture_ids = _resolve_fixture_ids_from_prompt(prompt, fixtures_result)
        color_name = _extract_color_name(prompt)
        if fixture_ids and (color_name is None or all(fixture_id.startswith("parcan") for fixture_id in fixture_ids)):
            used_tools.append("mcp_read_beats")
            beat_seconds = _estimate_beat_seconds(await call_mcp("mcp_read_beats", {"start_time": round(max(0.0, cue_time - 1.0), 3), "end_time": round(cue_time + 2.0, 3)}), cue_time) or 0.5
            duration = max(0.1, round((_extract_beat_duration(prompt) or 1.0) * beat_seconds, 3))
            data: Dict[str, Any] = {}
            if color_name is not None:
                data["channels"] = [color_name]
            return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": cue_time, "fixture_id": fixture_id, "effect": "flash", "duration": duration, "data": dict(data)} for fixture_id in fixture_ids]})}
    if cue_time is not None and "full" in lowered and any(word in lowered for word in ["set", "make", "turn"]):
        used_tools.append("mcp_read_fixtures")
        fixture_ids = _resolve_fixture_ids_from_prompt(prompt, await call_mcp("mcp_read_fixtures", {}))
        if fixture_ids:
            return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": cue_time, "fixture_id": fixture_id, "effect": "full", "duration": 0.0, "data": {}} for fixture_id in fixture_ids]})}
    if any(word in lowered for word in ["flash", "effect", "add"]) and "each section" in lowered and "prism" in lowered:
        effect_name = _extract_effect_name(prompt)
        if effect_name is not None:
            used_tools.extend(["mcp_read_sections", "mcp_read_fixtures"])
            section_times = _section_start_times(await call_mcp("mcp_read_sections", {}))
            fixtures_result = await call_mcp("mcp_read_fixtures", {})
            fixture_ids = _resolve_prism_fixture_ids(fixtures_result) if "left" not in lowered else [fixture_id for fixture_id in _resolve_prism_fixture_ids(fixtures_result) if fixture_id.endswith("_l")]
            if section_times and fixture_ids:
                return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": section_time, "fixture_id": fixture_id, "effect": effect_name, "duration": 0.5, "data": {}} for section_time in section_times for fixture_id in fixture_ids]})}
    if any(word in lowered for word in ["add", "apply"]) and "prism" in lowered and "change" in lowered:
        chord_transition = _extract_chord_transition(prompt)
        effect_name = _extract_effect_name(prompt)
        if chord_transition is not None and effect_name is not None:
            used_tools.extend(["mcp_read_chords", "mcp_read_fixtures"])
            transition_time = _find_chord_transition_time(await call_mcp("mcp_read_chords", {}), chord_transition[0], chord_transition[1])
            prism_fixture_ids = _resolve_prism_fixture_ids(await call_mcp("mcp_read_fixtures", {}))
            if transition_time is not None and prism_fixture_ids:
                return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": transition_time, "fixture_id": fixture_id, "effect": effect_name, "duration": 0.5, "data": {}} for fixture_id in prism_fixture_ids]})}
    if any(word in lowered for word in ["set", "make", "turn"]) and ("parcan" in lowered or "proton" in lowered) and "chord" in lowered:
        chord_label = _extract_chord_label(prompt)
        rgb = _color_name_to_rgb(_extract_color_name(prompt) or "") if _extract_color_name(prompt) is not None else None
        if chord_label and rgb is not None:
            used_tools.extend(["mcp_read_chords", "mcp_read_fixtures"])
            chord_times = _find_chord_times(await call_mcp("mcp_read_chords", {}), chord_label)
            fixtures_result = await call_mcp("mcp_read_fixtures", {})
            fixture_ids = _resolve_parcan_fixture_ids(fixtures_result) if "parcan" in lowered else _resolve_proton_fixture_ids(fixtures_result)
            if chord_times and fixture_ids:
                return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": chord_time, "fixture_id": fixture_id, "effect": "full", "duration": 0.0, "data": dict(rgb)} for chord_time in chord_times for fixture_id in fixture_ids]})}
    if ("turn off" in lowered or "off" in lowered) and "proton" in lowered and "chord" in lowered:
        chord_label = _extract_chord_label(prompt)
        if chord_label:
            used_tools.extend(["mcp_read_chords", "mcp_read_fixtures"])
            chord_times = _find_chord_times(await call_mcp("mcp_read_chords", {}), chord_label)
            fixture_ids = _resolve_proton_fixture_ids(await call_mcp("mcp_read_fixtures", {}))
            if chord_times and fixture_ids:
                return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": chord_time, "fixture_id": fixture_id, "effect": "blackout", "duration": 0.0, "data": {}} for chord_time in chord_times for fixture_id in fixture_ids]})}
    if "none" in lowered and ("prism" in lowered or "fixture" in lowered) and (("fade out" in lowered or "from 1 to 0" in lowered) or "turn off" in lowered or "off" in lowered):
        used_tools.extend(["mcp_read_chords", "mcp_read_fixtures"])
        chords_result = await call_mcp("mcp_read_chords", {})
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        none_spans = _find_chord_spans(chords_result, "none")
        if none_spans:
            if "prism" in lowered and ("fade out" in lowered or "from 1 to 0" in lowered):
                fixture_ids = _resolve_prism_fixture_ids(fixtures_result)
                return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": start_time, "fixture_id": fixture_id, "effect": "fade_out", "duration": max(0.1, end_time - start_time), "data": {}} for start_time, end_time in none_spans for fixture_id in fixture_ids]})} if fixture_ids else None
            parcan_fixture_ids = _resolve_parcan_fixture_ids(fixtures_result)
            dimmable_fixture_ids = _resolve_non_parcan_fixture_ids(fixtures_result)
            entries = [{"time": start_time, "fixture_id": fixture_id, "effect": "blackout", "duration": 0.0, "data": {}} for start_time, _end_time in none_spans for fixture_id in parcan_fixture_ids]
            entries.extend({"time": start_time, "fixture_id": fixture_id, "effect": "fade_out", "duration": max(0.1, end_time - start_time), "data": {}} for start_time, end_time in none_spans for fixture_id in dimmable_fixture_ids)
            if entries:
                return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": entries})}
    if "clear" in lowered and "cue" in lowered and _is_full_cue_clear_request(prompt):
        return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_clear_all", {})}
    if "clear" in lowered and "cue" in lowered and section_name:
        used_tools.append("mcp_find_section")
        section = ((await call_mcp("mcp_find_section", {"section_name": section_name})).get("data") or {}).get("section") or {}
        if section:
            return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_clear_range", {"start_time": float(section.get("start_s", 0.0)), "end_time": float(section.get("end_s", 0.0))})}
    return None