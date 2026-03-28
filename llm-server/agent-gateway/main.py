import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PATH_INSERTED = False
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
    PATH_INSERTED = True

from app import _event_stream, app, chat_completions, debug_mcp_tools, health
from config import LLM_BASE_URL, MCP_BASE_URL, MCP_TOOL_MAP, TOOLS
from fast_path import router as _fast_path_router_module
from fast_path.answer_text import (
    _build_chords_in_bar_answer_text,
    _build_cursor_answer_text,
    _build_cursor_section_next_beat_answer_text,
    _build_first_chord_answer_text,
    _build_left_fixtures_answer_text,
    _build_loudest_section_answer_text,
    _build_pois_answer_text,
    _build_prism_effects_answer_text,
    _build_section_count_answer_text,
)
from fast_path.handlers import chaser as _fast_path_chaser_module
from fast_path.handlers import cue_proposals as _fast_path_cue_module
from fast_path.handlers import informational as _fast_path_informational_module
from fast_path.handlers import movement as _fast_path_movement_module
from fast_path.extractors.chords import (
    _extract_chord_label,
    _extract_chord_transition,
    _find_chord_spans,
    _find_chord_times,
    _find_chord_transition_time,
    _normalize_chord_label,
)
from fast_path.extractors.effects import _color_name_to_rgb, _extract_color_name, _extract_effect_name
from fast_path.extractors.fixtures import (
    _resolve_fixture_ids_from_prompt,
    _resolve_left_prism_fixture_ids,
    _resolve_non_parcan_fixture_ids,
    _resolve_parcan_fixture_ids,
    _resolve_prism_fixture_ids,
    _resolve_proton_fixture_ids,
    _resolve_right_prism_fixture_ids,
    _resolve_target_prism_fixture_ids,
)
from fast_path.extractors.poi import _extract_ordered_poi_ids, _extract_poi_transition, _resolve_poi_id
from fast_path.extractors.sections import _extract_section_name, _extract_section_reference, _find_section_occurrence, _section_start_times
from fast_path.extractors.timing import (
    _estimate_beat_seconds,
    _extract_bar_beat,
    _extract_beat_duration,
    _extract_time_seconds,
    _find_first_beat_at_or_after,
    _find_next_beat_after,
    _find_previous_beat_time,
)
from fast_path.proposals import _describe_cue_add_entries, _proposal_for_tool
from llm_client import _chunk_text, _llm_complete
from gateway_mcp.arguments import _expand_subdivision_times, _require_song_arg
from gateway_mcp.client import _call_mcp_tool, call_mcp
from messages import _latest_user_prompt
from gateway_models import ChatRequest
from prompt.factual_answers import (
    _build_first_effect_answer_messages,
    _build_fixtures_at_bar_answer_messages,
    _build_left_fixtures_answer_messages,
    _build_loudness_answer_messages,
)
from prompt.guidance import _build_query_guidance, _inject_query_guidance
from prompt.instructions import TOOL_OUTPUT_SYSTEM_MESSAGE, _bar_beat_time_instruction, _song_name_mention_instruction
from prompt.lookup_answers import (
    _build_chord_answer_messages,
    _build_cursor_answer_messages,
    _build_section_answer_messages,
    _is_section_timing_question,
)
from rendering.results import (
    _format_bar_beat_match,
    _format_beats,
    _format_chasers,
    _format_chord_match,
    _format_chords,
    _format_cue_window,
    _format_cursor,
    _format_fixtures,
    _format_generic_result,
    _format_loudness,
    _format_pois,
    _format_section_match,
    _format_sections,
    _render_tool_result,
)

async def _run_stream_fast_path(messages):
    _fast_path_chaser_module.call_mcp = call_mcp
    _fast_path_cue_module.call_mcp = call_mcp
    _fast_path_informational_module.call_mcp = call_mcp
    _fast_path_movement_module.call_mcp = call_mcp
    return await _fast_path_router_module._run_stream_fast_path(messages)


__all__ = [
    "_event_stream",
    "_build_chords_in_bar_answer_text",
    "_build_chord_answer_messages",
    "_build_cursor_answer_messages",
    "_build_cursor_answer_text",
    "_build_cursor_section_next_beat_answer_text",
    "_build_first_chord_answer_text",
    "_build_first_effect_answer_messages",
    "_build_fixtures_at_bar_answer_messages",
    "_build_left_fixtures_answer_messages",
    "_build_left_fixtures_answer_text",
    "_build_loudest_section_answer_text",
    "_build_loudness_answer_messages",
    "_build_pois_answer_text",
    "_build_prism_effects_answer_text",
    "_build_query_guidance",
    "_build_section_answer_messages",
    "_build_section_count_answer_text",
    "_call_mcp_tool",
    "_chunk_text",
    "_color_name_to_rgb",
    "_describe_cue_add_entries",
    "_estimate_beat_seconds",
    "_expand_subdivision_times",
    "_extract_bar_beat",
    "_extract_beat_duration",
    "_extract_chord_label",
    "_extract_chord_transition",
    "_extract_color_name",
    "_extract_effect_name",
    "_extract_ordered_poi_ids",
    "_extract_poi_transition",
    "_extract_section_name",
    "_extract_section_reference",
    "_extract_time_seconds",
    "_find_chord_spans",
    "_find_chord_times",
    "_find_chord_transition_time",
    "_find_first_beat_at_or_after",
    "_find_next_beat_after",
    "_find_previous_beat_time",
    "_find_section_occurrence",
    "_format_bar_beat_match",
    "_format_beats",
    "_format_chasers",
    "_format_chord_match",
    "_format_chords",
    "_format_cue_window",
    "_format_cursor",
    "_format_fixtures",
    "_format_generic_result",
    "_format_loudness",
    "_format_pois",
    "_format_section_match",
    "_format_sections",
    "_inject_query_guidance",
    "_is_section_timing_question",
    "_latest_user_prompt",
    "_llm_complete",
    "_normalize_chord_label",
    "_proposal_for_tool",
    "_render_tool_result",
    "_require_song_arg",
    "_resolve_fixture_ids_from_prompt",
    "_resolve_left_prism_fixture_ids",
    "_resolve_non_parcan_fixture_ids",
    "_resolve_parcan_fixture_ids",
    "_resolve_poi_id",
    "_resolve_prism_fixture_ids",
    "_resolve_proton_fixture_ids",
    "_resolve_right_prism_fixture_ids",
    "_resolve_target_prism_fixture_ids",
    "_run_stream_fast_path",
    "_section_start_times",
    "_song_name_mention_instruction",
    "TOOL_OUTPUT_SYSTEM_MESSAGE",
    "app",
    "call_mcp",
    "chat_completions",
    "ChatRequest",
    "debug_mcp_tools",
    "health",
    "LLM_BASE_URL",
    "MCP_BASE_URL",
    "MCP_TOOL_MAP",
    "TOOLS",
]

if PATH_INSERTED:
    try:
        sys.path.remove(str(CURRENT_DIR))
    except ValueError:
        pass
