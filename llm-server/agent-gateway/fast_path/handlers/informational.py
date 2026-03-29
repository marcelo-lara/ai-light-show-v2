from typing import Any, Dict, List, Optional

from fast_path.answer_text import _build_chords_in_bar_answer_text, _build_cursor_answer_text, _build_cursor_section_next_beat_answer_text, _build_first_chord_answer_text, _build_fixture_effects_answer_text, _build_fixture_type_count_answer_text, _build_fixture_type_list_answer_text, _build_left_fixtures_answer_text, _build_loudest_section_answer_text, _build_pois_answer_text, _build_prism_effects_answer_text, _build_section_count_answer_text
from fast_path.extractors.chords import _extract_chord_label
from fast_path.extractors.fixtures import _resolve_fixture_ids_from_prompt, _resolve_moving_head_fixture_ids
from fast_path.extractors.sections import _extract_section_reference
from fast_path.extractors.timing import _extract_bar_beat
from gateway_mcp.client import call_mcp
from prompt.factual_answers import _build_first_effect_answer_messages, _build_fixtures_at_bar_answer_messages, _build_loudness_answer_messages


async def try_informational_fast_path(messages: List[Dict[str, Any]], prompt: str, lowered: str) -> Optional[Dict[str, Any]]:
    section_name, _section_occurrence = _extract_section_reference(prompt)
    used_tools: List[str] = []
    if "prism" in lowered and "effect" in lowered and any(word in lowered for word in ["available", "could", "render", "list"]):
        used_tools.append("mcp_read_fixtures")
        answer_text = _build_prism_effects_answer_text(await call_mcp("mcp_read_fixtures", {}))
        if answer_text is not None:
            return {"used_tools": used_tools, "answer_text": answer_text}
    if "how many" in lowered and ("moving head" in lowered or "moving heads" in lowered):
        used_tools.append("mcp_read_fixtures")
        answer_text = _build_fixture_type_count_answer_text(await call_mcp("mcp_read_fixtures", {}), "moving_head", "moving heads")
        if answer_text is not None:
            return {"used_tools": used_tools, "answer_text": answer_text}
    if any(phrase in lowered for phrase in ["which moving heads", "what moving heads", "what fixtures are moving heads", "which fixtures are moving heads"]):
        used_tools.append("mcp_read_fixtures")
        answer_text = _build_fixture_type_list_answer_text(await call_mcp("mcp_read_fixtures", {}), "moving_head", "moving heads")
        if answer_text is not None:
            return {"used_tools": used_tools, "answer_text": answer_text}
    if "effect" in lowered and any(word in lowered for word in ["available", "can", "could", "perform", "render", "support"]):
        if "moving head" in lowered or "moving heads" in lowered or "el-150" in lowered or "el150" in lowered or "head_el150" in lowered:
            used_tools.append("mcp_read_fixtures")
            fixtures_result = await call_mcp("mcp_read_fixtures", {})
            fixture_ids = _resolve_fixture_ids_from_prompt(prompt, fixtures_result)
            if not fixture_ids and ("moving head" in lowered or "moving heads" in lowered):
                fixture_ids = _resolve_moving_head_fixture_ids(fixtures_result)
            answer_text = _build_fixture_effects_answer_text(fixtures_result, fixture_ids, "moving head")
            if answer_text is not None:
                return {"used_tools": used_tools, "answer_text": answer_text}
    if "available" in lowered and any(token in lowered for token in ["poi", "pois"]):
        used_tools.append("mcp_read_pois")
        answer_text = _build_pois_answer_text(await call_mcp("mcp_read_pois", {}))
        if answer_text is not None:
            return {"used_tools": used_tools, "answer_text": answer_text}
    if "how many" in lowered and "section" in lowered:
        used_tools.append("mcp_read_sections")
        answer_text = _build_section_count_answer_text(await call_mcp("mcp_read_sections", {}))
        if answer_text is not None:
            return {"used_tools": used_tools, "answer_text": answer_text}
    if "which" in lowered and "chord" in lowered and "bar" in lowered:
        position = _extract_bar_beat(prompt)
        if position is not None:
            used_tools.append("mcp_read_chords")
            answer_text = _build_chords_in_bar_answer_text(await call_mcp("mcp_read_chords", {"start_bar": position[0], "end_bar": position[0]}), position[0])
            if answer_text is not None:
                return {"used_tools": used_tools, "answer_text": answer_text}
    if "section am i in" in lowered and "next beat" in lowered:
        used_tools.append("mcp_read_cursor")
        answer_text = _build_cursor_section_next_beat_answer_text(await call_mcp("mcp_read_cursor", {}))
        if answer_text is not None:
            return {"used_tools": used_tools, "answer_text": answer_text}
    if "loudest section" in lowered:
        used_tools.append("mcp_read_sections")
        sections_result = await call_mcp("mcp_read_sections", {})
        sections = ((sections_result.get("data") or {}).get("sections") or []) if isinstance(sections_result, dict) and sections_result.get("ok") else []
        best_section = None
        best_loudness = None
        best_average = None
        for section in sections:
            used_tools.append("mcp_read_loudness")
            loudness_result = await call_mcp("mcp_read_loudness", {"section": str(section.get("name") or "")})
            if not isinstance(loudness_result, dict) or not loudness_result.get("ok"):
                continue
            average = float(((loudness_result.get("data") or {}).get("average") or 0.0))
            if best_average is None or average > best_average:
                best_average = average
                best_section = section
                best_loudness = loudness_result
        answer_text = _build_loudest_section_answer_text(best_section or {}, best_loudness or {})
        if answer_text is not None:
            return {"used_tools": used_tools, "answer_text": answer_text}
    if "first occurrence" in lowered and "chord" in lowered:
        chord_label = _extract_chord_label(prompt)
        if chord_label:
            used_tools.append("mcp_find_chord")
            answer_text = _build_first_chord_answer_text(await call_mcp("mcp_find_chord", {"chord": chord_label, "occurrence": 1}))
            if answer_text is not None:
                return {"used_tools": used_tools, "answer_text": answer_text}
    if "cursor" in lowered:
        used_tools.append("mcp_read_cursor")
        answer_text = _build_cursor_answer_text(await call_mcp("mcp_read_cursor", {}))
        if answer_text is not None:
            return {"used_tools": used_tools, "answer_text": answer_text}
    if "first effect" in lowered and section_name:
        used_tools.append("mcp_find_section")
        section_result = await call_mcp("mcp_find_section", {"section_name": section_name})
        section = ((section_result.get("data") or {}).get("section") or {}) if isinstance(section_result, dict) else {}
        if section:
            used_tools.append("mcp_read_cue_window")
            cue_result = await call_mcp("mcp_read_cue_window", {"start_time": float(section.get("start_s", 0.0)), "end_time": float(section.get("end_s", 0.0))})
            if ((cue_result.get("data") or {}).get("entries") or []) if isinstance(cue_result, dict) else []:
                return {"used_tools": used_tools, "answer_messages": _build_first_effect_answer_messages(messages, section_result, cue_result)}
    if "loud" in lowered and section_name:
        used_tools.append("mcp_read_loudness")
        loudness_result = await call_mcp("mcp_read_loudness", {"section": section_name})
        if isinstance(loudness_result, dict) and loudness_result.get("ok"):
            return {"used_tools": used_tools, "answer_messages": _build_loudness_answer_messages(messages, loudness_result)}
    if "fixture" in lowered and "bar" in lowered:
        position = _extract_bar_beat(prompt)
        if position is not None:
            used_tools.append("mcp_find_bar_beat")
            position_result = await call_mcp("mcp_find_bar_beat", {"bar": position[0], "beat": position[1]})
            resolved = ((position_result.get("data") or {}).get("position") or {}) if isinstance(position_result, dict) else {}
            if resolved:
                used_tools.append("mcp_read_cue_window")
                cue_result = await call_mcp("mcp_read_cue_window", {"start_time": float(resolved.get("time", 0.0)), "end_time": float(resolved.get("time", 0.0))})
                if ((cue_result.get("data") or {}).get("entries") or []) if isinstance(cue_result, dict) else []:
                    return {"used_tools": used_tools, "answer_messages": _build_fixtures_at_bar_answer_messages(messages, position_result, cue_result)}
    if "fixture" in lowered and "left" in lowered:
        used_tools.append("mcp_read_fixtures")
        answer_text = _build_left_fixtures_answer_text(await call_mcp("mcp_read_fixtures", {}))
        if answer_text is not None:
            return {"used_tools": used_tools, "answer_text": answer_text}
    return None