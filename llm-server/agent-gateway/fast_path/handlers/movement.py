from typing import Any, Dict, List, Optional

from fast_path.extractors.fixtures import _resolve_target_prism_fixture_ids
from fast_path.extractors.poi import _extract_poi_transition, _resolve_poi_id
from fast_path.extractors.sections import _extract_section_reference, _find_section_occurrence
from fast_path.extractors.timing import _find_first_beat_at_or_after, _find_next_beat_after, _find_previous_beat_time
from fast_path.proposals import _proposal_for_tool
from gateway_mcp.client import call_mcp


async def try_movement_fast_path(prompt: str, lowered: str) -> Optional[Dict[str, Any]]:
    section_name, section_occurrence = _extract_section_reference(prompt)
    if not section_name:
        return None
    used_tools: List[str] = []
    if any(word in lowered for word in ["move", "point", "aim"]) and "prism" in lowered and "one beat before" in lowered:
        used_tools.extend(["mcp_read_sections", "mcp_read_fixtures", "mcp_read_pois"])
        sections_result = await call_mcp("mcp_read_sections", {})
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        pois_result = await call_mcp("mcp_read_pois", {})
        section = _find_section_occurrence(sections_result, section_name, section_occurrence)
        poi_id = _resolve_poi_id(prompt, pois_result)
        if section is not None and poi_id:
            fixture_ids = _resolve_target_prism_fixture_ids(prompt, fixtures_result)
            if fixture_ids:
                section_start = float(section.get("start_s", 0.0) or 0.0)
                used_tools.append("mcp_read_beats")
                cue_time = _find_previous_beat_time(await call_mcp("mcp_read_beats", {"end_time": section_start}), section_start)
                if cue_time is not None:
                    duration = max(0.1, round(section_start - cue_time, 3))
                    return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": cue_time, "fixture_id": fixture_id, "effect": "move_to_poi", "duration": duration, "data": {"target_POI": poi_id}} for fixture_id in fixture_ids]})}
    if any(word in lowered for word in ["move", "point", "aim"]) and "prism" in lowered and any(phrase in lowered for phrase in ["start of", "first beat"]):
        used_tools.extend(["mcp_read_sections", "mcp_read_fixtures", "mcp_read_pois"])
        sections_result = await call_mcp("mcp_read_sections", {})
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        pois_result = await call_mcp("mcp_read_pois", {})
        section = _find_section_occurrence(sections_result, section_name, section_occurrence)
        poi_id = _resolve_poi_id(prompt, pois_result)
        if section is not None and poi_id:
            fixture_ids = _resolve_target_prism_fixture_ids(prompt, fixtures_result)
            if fixture_ids:
                cue_time = float(section.get("start_s", 0.0) or 0.0)
                return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": cue_time, "fixture_id": fixture_id, "effect": "move_to_poi", "duration": 0.0, "data": {"target_POI": poi_id}} for fixture_id in fixture_ids]})}
    if any(word in lowered for word in ["seek", "sweep"]) and "prism" in lowered and ("one beat before" in lowered or "first beat" in lowered):
        effect_name = "seek" if "seek" in lowered else "sweep"
        used_tools.extend(["mcp_read_sections", "mcp_read_fixtures", "mcp_read_pois"])
        sections_result = await call_mcp("mcp_read_sections", {})
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        pois_result = await call_mcp("mcp_read_pois", {})
        section = _find_section_occurrence(sections_result, section_name, section_occurrence)
        poi_transition = _extract_poi_transition(prompt, pois_result)
        if section is not None and poi_transition is not None:
            fixture_ids = _resolve_target_prism_fixture_ids(prompt, fixtures_result)
            if fixture_ids:
                section_start = float(section.get("start_s", 0.0) or 0.0)
                if "one beat before" in lowered:
                    used_tools.append("mcp_read_beats")
                    cue_time = _find_previous_beat_time(await call_mcp("mcp_read_beats", {"end_time": section_start}), section_start)
                    duration = max(0.1, round(section_start - cue_time, 3)) if cue_time is not None else None
                else:
                    section_end = float(section.get("end_s", section_start) or section_start)
                    used_tools.append("mcp_read_beats")
                    beats_result = await call_mcp("mcp_read_beats", {"start_time": section_start, "end_time": section_end})
                    cue_time = _find_first_beat_at_or_after(beats_result, section_start)
                    next_beat_time = _find_next_beat_after(beats_result, cue_time) if cue_time is not None else None
                    duration = max(0.1, round((next_beat_time - cue_time) if next_beat_time is not None else 0.5, 3)) if cue_time is not None else None
                if cue_time is not None and duration is not None:
                    start_poi, subject_poi, end_poi = poi_transition
                    data: Dict[str, Any] = {"start_POI": start_poi, "subject_POI": subject_poi}
                    if effect_name == "sweep" and end_poi:
                        data["end_POI"] = end_poi
                    return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": [{"time": cue_time, "fixture_id": fixture_id, "effect": effect_name, "duration": duration, "data": dict(data)} for fixture_id in fixture_ids]})}
    return None