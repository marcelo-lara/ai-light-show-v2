import re
from typing import Any, Dict, List, Optional

from messages import _latest_user_prompt


def _requested_poi_action(prompt: str) -> Optional[str]:
    if "orbit" in prompt:
        return "orbit"
    if "sweep" in prompt:
        return "sweep"
    if any(word in prompt for word in ["move", "point", "aim"]):
        return "move_to_poi"
    return None


def _is_fixture_movement_request(prompt: str) -> bool:
    return _requested_poi_action(prompt) is not None and any(token in prompt for token in ["moving head", "moving heads", "fixture", "prism"])


def _has_explicit_time_or_section(prompt: str) -> bool:
    if re.search(r"\b(bar|beat|second|seconds)\b", prompt):
        return True
    if re.search(r"\b\d+(?:\.\d+)?s\b", prompt):
        return True
    return any(word in prompt for word in ["intro", "verse", "chorus", "instrumental", "outro", "section", "cursor"])


def _tool_history(messages: List[Dict[str, Any]], tool_names: List[str]) -> set[str]:
    history = {str(tool_name) for tool_name in tool_names}
    for message in messages:
        if message.get("role") != "assistant":
            continue
        for tool_call in message.get("tool_calls") or []:
            function = tool_call.get("function") or {}
            tool_name = str(function.get("name") or "").strip()
            if tool_name:
                history.add(tool_name)
    return history


def _build_query_guidance(messages: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    prompt = _latest_user_prompt(messages).lower()
    if not prompt:
        return None
    hints: List[str] = []
    if "cursor" in prompt:
        hints.append("For cursor questions, call mcp_read_cursor and answer with time_s plus bar.beat.")
    if "chord" in prompt:
        hints.append("For chord questions, use mcp_find_chord for exact occurrence lookups or mcp_read_chords for broader windows. Do not use mcp_find_section unless the user explicitly asks about a section boundary.")
    if any(word in prompt for word in ["add", "apply"]) and "prism" in prompt and "change" in prompt and " to " in prompt:
        hints.append("For cue additions tied to a chord change, resolve the full chord stream with mcp_read_chords, find the requested adjacent transition, resolve target fixtures with mcp_read_fixtures, and propose_cue_add_entries for the matching fixtures at that transition time.")
    if any(word in prompt for word in ["add", "flash", "effect"]) and "each section" in prompt and "prism" in prompt:
        hints.append("For requests like first beat of each section on the left prism, resolve section starts with mcp_read_sections, resolve the target fixture with mcp_read_fixtures, and propose_cue_add_entries with one entry per section start.")
    if any(word in prompt for word in ["move", "point", "aim", "orbit", "sweep"]) and "prism" in prompt and any(word in prompt for word in ["intro", "verse", "chorus", "instrumental", "outro", "section"]):
        hints.append("For fixture movement requests that mention named places like piano, table, or center, treat those place names as POIs. Resolve the target section timing, validate the POIs with mcp_read_pois, resolve the target fixture with mcp_read_fixtures, and propose_cue_add_entries using move_to_poi or another POI-aware effect. Do not use chord tools unless the user explicitly asks about chords.")
    if "loud" in prompt:
        hints.append("For loudness questions, use mcp_read_loudness. If the prompt names a section like verse or chorus, pass that section or resolve it first.")
    if any(token in prompt for token in ["section metadata", "sections metadata", "description", "descriptions", "hint", "hints"]) and any(token in prompt for token in ["section", "intro", "verse", "chorus", "instrumental", "outro"]):
        hints.append("For section metadata drafting or review, read mcp_read_section_analysis first. Use it as the grounded source for section energy, harmonic patterns, and bass/drums/vocals support before writing descriptions or hints.")
    if any(token in prompt for token in ["moving head", "moving heads", "el-150", "el150"]) or ("fixture" in prompt and any(token in prompt for token in ["effect", "effects", "support", "supports", "how many", "count"])):
        hints.append("For fixture inventory, type, or capability questions, call mcp_read_fixtures and answer from the returned fixture ids, names, type, capabilities, and supported_effects fields. If the user asks what an effect does after that, read mcp_read_effects for effect descriptions.")
    if _is_fixture_movement_request(prompt):
        hints.append("For POI-aware fixture action requests, resolve fixtures with mcp_read_fixtures and locations with mcp_read_pois before answering. If the request has no explicit time or section, read mcp_read_cursor and use the current cursor time for the proposal.")
        hints.append("For direct point, move, or aim requests, propose_cue_add_entries with move_to_poi using data.target_POI. For orbit requests, use effect orbit with data.start_POI and data.subject_POI. For sweep requests, use effect sweep with data.start_POI, data.subject_POI, and data.end_POI when the prompt gives a third POI.")
        hints.append("For type-qualified phrases like 'el-150 moving head', match the qualifier against fixture ids and names inside the requested fixture type. If there is no match, say that clearly and list the available matching fixtures instead of inventing one.")
    if "first effect" in prompt or ("effect" in prompt and any(word in prompt for word in ["verse", "chorus", "intro", "instrumental", "outro"])):
        hints.append("For section effect questions, first resolve the section with mcp_find_section, then inspect the cue entries in that section using mcp_read_cue_window. Answer from the earliest cue entry in that window.")
    if "clear" in prompt and "cue" in prompt:
        hints.append("For cue clearing requests, resolve the target section first and then propose_cue_clear_range with that exact section start and end time. For full-sheet requests like clear all the cue, entire cue, or all cues, use propose_cue_clear_all. Never propose a 0 to 0 range.")
    if "fixture" in prompt and "left" in prompt:
        hints.append("For left-side fixture questions, call mcp_read_fixtures and answer with the matching fixture ids. In this rig, left fixtures use ids ending in _l or _pl.")
    if "fixture" in prompt and re.search(r"\bbar\s+\d+", prompt):
        hints.append("For fixture-at-bar questions, resolve the exact musical position first with mcp_find_bar_beat. If the user gives only a bar number, use beat 1 for the bar start, then inspect cues at that resolved time with mcp_read_cue_window.")
    if "chaser" in prompt:
        hints.append("For chaser requests, resolve the target section first, inspect available chasers with mcp_read_chasers, and then use propose_chaser_apply with the section start time and the best-matching chaser id.")
    if not hints:
        return None
    return {"role": "system", "content": "Tool routing guidance:\n- " + "\n- ".join(hints)}


def _build_followup_tool_guidance(messages: List[Dict[str, Any]], tool_names: List[str]) -> Optional[Dict[str, str]]:
    prompt = _latest_user_prompt(messages).lower()
    if not prompt or not _is_fixture_movement_request(prompt):
        return None
    hints: List[str] = []
    requested_action = _requested_poi_action(prompt) or "move_to_poi"
    history = _tool_history(messages, tool_names)
    has_fixtures = "mcp_read_fixtures" in history
    has_pois = "mcp_read_pois" in history
    has_cursor = "mcp_read_cursor" in history
    explicit_time_or_section = _has_explicit_time_or_section(prompt)
    if has_fixtures and not has_pois:
        hints.append("You already have fixture candidates. Do not answer yet. Call mcp_read_pois now to resolve the destination POI id mentioned by the user.")
    if has_fixtures and has_pois and not explicit_time_or_section and not has_cursor:
        hints.append("The request does not include an explicit time or section. Do not answer yet. Call mcp_read_cursor now and use Cursor proposal_time as the cue time.")
    if has_fixtures and has_pois and (explicit_time_or_section or has_cursor):
        if requested_action == "orbit":
            hints.append("You now have enough information to act. If the resolved fixture supports orbit, call propose_cue_add_entries with one entry using effect orbit, data.start_POI and data.subject_POI set to the resolved ordered POI ids, and the resolved time or cursor proposal_time.")
        elif requested_action == "sweep":
            hints.append("You now have enough information to act. If the resolved fixture supports sweep, call propose_cue_add_entries with one entry using effect sweep, data.start_POI and data.subject_POI set to the resolved ordered POI ids, add data.end_POI when the prompt names a third POI, and use the resolved time or cursor proposal_time.")
        else:
            hints.append("You now have enough information to act. If the resolved fixture supports move_to_poi, call propose_cue_add_entries with one entry using effect move_to_poi, data.target_POI set to the resolved POI id, and the resolved time or cursor proposal_time.")
        hints.append("Do not answer with missing-information text once the required fixture, POI, and timing facts are available from tools.")
    if not hints:
        return None
    return {"role": "system", "content": "Follow-up tool guidance:\n- " + "\n- ".join(hints)}


def _movement_followup_allowed_tools(messages: List[Dict[str, Any]], tool_names: List[str]) -> Optional[List[str]]:
    prompt = _latest_user_prompt(messages).lower()
    if not prompt or not _is_fixture_movement_request(prompt):
        return None
    history = _tool_history(messages, tool_names)
    has_fixtures = "mcp_read_fixtures" in history
    has_pois = "mcp_read_pois" in history
    has_cursor = "mcp_read_cursor" in history
    explicit_time_or_section = _has_explicit_time_or_section(prompt)
    if has_fixtures and not has_pois:
        return ["mcp_read_pois"]
    if has_fixtures and has_pois and not explicit_time_or_section and not has_cursor:
        return ["mcp_read_cursor"]
    if has_fixtures and has_pois and (explicit_time_or_section or has_cursor):
        return ["propose_cue_add_entries"]
    return None


def _inject_query_guidance(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    guidance = _build_query_guidance(messages)
    if guidance is None:
        return list(messages)
    return list(messages) + [guidance]
