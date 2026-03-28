import re
from typing import Any, Dict, List, Optional

from messages import _latest_user_prompt


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


def _inject_query_guidance(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    guidance = _build_query_guidance(messages)
    if guidance is None:
        return list(messages)
    return list(messages) + [guidance]