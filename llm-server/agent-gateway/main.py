import json
import logging
import os
import difflib
import re
from typing import Any, Dict, List, Optional

import httpx
import orjson
from fastmcp import Client
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

log = logging.getLogger("agent-gateway")
logging.basicConfig(level=logging.INFO)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://llm-server:8080")
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://backend:5001/mcp")

# ---- OpenAI-style tools exposed to the model ----
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "mcp_read_sections",
            "description": "Read the song sections with exact names, time ranges, and resolved start/end bars and beats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "string"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_find_section",
            "description": "Find one exact section by name for the current song. Use this for questions like 'where does the verse start?' or 'when does the chorus end?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "section_name": {"type": "string"}
                },
                "required": ["section_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_beats",
            "description": "Read beat entries with time, bar, and beat values for an optional time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "string"},
                    "start_time": {"type": "number"},
                    "end_time": {"type": "number"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_bar_beats",
            "description": "Read beat entries by musical position using start/end bars and beats instead of seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "string"},
                    "start_bar": {"type": "integer"},
                    "start_beat": {"type": "integer"},
                    "end_bar": {"type": "integer"},
                    "end_beat": {"type": "integer"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_find_bar_beat",
            "description": "Find one exact beat row for a specific bar and beat and return its exact time and chord context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "string"},
                    "bar": {"type": "integer"},
                    "beat": {"type": "integer"}
                },
                "required": ["bar", "beat"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_find_chord",
            "description": "Find an exact chord occurrence by label and return its time, bar, and beat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "string"},
                    "chord": {"type": "string"},
                    "occurrence": {"type": "integer"}
                },
                "required": ["chord"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_chords",
            "description": "Read chord changes for the current song or a time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "string"},
                    "start_time": {"type": "number"},
                    "end_time": {"type": "number"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_cue_window",
            "description": "Read cue entries in a specific time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "number"},
                    "end_time": {"type": "number"}
                },
                "required": ["start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_fixtures",
            "description": "Read the fixture list including ids, names, and positions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_pois",
            "description": "Read the available POIs and their ids. Use this when a request mentions named stage locations like piano, table, or center.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_chasers",
            "description": "Read the available chaser definitions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_cursor",
            "description": "Read the current transport cursor time, section, and nearest bar.beat.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_loudness",
            "description": "Read loudness statistics for a time window or section.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "string"},
                    "section": {"type": "string"},
                    "start_time": {"type": "number"},
                    "end_time": {"type": "number"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_cue_clear_range",
            "description": "Propose clearing cue entries in a specific time range. Use for destructive cue sheet edits that need confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "number"},
                    "end_time": {"type": "number"}
                },
                "required": ["start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_cue_add_entries",
            "description": "Propose adding one or more effect cue entries. Use for cue edits that need confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "time": {"type": "number"},
                                "fixture_id": {"type": "string"},
                                "effect": {"type": "string"},
                                "duration": {"type": "number"},
                                "data": {"type": "object"}
                            },
                            "required": ["time", "fixture_id", "effect", "duration", "data"]
                        }
                    }
                },
                "required": ["entries"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_cue_clear_all",
            "description": "Propose clearing every cue entry from the current cue sheet. Use for destructive whole-sheet clears that need confirmation.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_chaser_apply",
            "description": "Propose adding a chaser cue entry starting at a time with repetitions. Use for cue changes that need confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chaser_id": {"type": "string"},
                    "start_time": {"type": "number"},
                    "repetitions": {"type": "integer"}
                },
                "required": ["chaser_id", "start_time", "repetitions"]
            }
        }
    },
]

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    model: Optional[str] = "local"
    temperature: Optional[float] = 0.2
    tool_choice: Optional[Any] = "auto"
    stream: Optional[bool] = False
    assistant_id: Optional[str] = "generic"

app = FastAPI()

# ---- MCP tool wrapper ----
MCP_TOOL_MAP = {
    "mcp_read_sections": "metadata_get_sections",
    "mcp_find_section": "metadata_find_section",
    "mcp_read_beats": "metadata_get_beats",
    "mcp_read_bar_beats": "metadata_get_bar_beats",
    "mcp_find_bar_beat": "metadata_find_bar_beat",
    "mcp_find_chord": "metadata_find_chord",
    "mcp_read_chords": "metadata_get_chords",
    "mcp_read_cue_window": "cues_get_window",
    "mcp_read_fixtures": "fixtures_list",
    "mcp_read_pois": "pois_list",
    "mcp_read_chasers": "chasers_list",
    "mcp_read_cursor": "transport_get_cursor",
    "mcp_read_loudness": "metadata_get_loudness",
}


def _require_song_arg(tool_name: str, args: Dict[str, Any]) -> str:
    song = args.get("song") or args.get("song_id")
    if not song:
        raise HTTPException(400, f"{tool_name} requires 'song' or 'song_id'")
    return str(song)


def _expand_subdivision_times(beat_times: List[float], subdivision: float) -> List[float]:
    if not beat_times:
        return []
    if subdivision >= 1.0:
        stride = max(1, int(round(subdivision)))
        return beat_times[::stride]

    steps = max(1, int(round(1.0 / subdivision)))
    expanded: List[float] = []
    for index in range(len(beat_times) - 1):
        start_time = beat_times[index]
        end_time = beat_times[index + 1]
        for offset in range(steps):
            expanded.append(start_time + ((end_time - start_time) * (offset / steps)))
    expanded.append(beat_times[-1])
    return [round(value, 6) for value in expanded]


def _latest_user_prompt(messages: List[Dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content") or "")
    return ""


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
    if any(word in prompt for word in ["move", "point", "aim", "seek", "sweep"]) and "prism" in prompt and any(word in prompt for word in ["intro", "verse", "chorus", "instrumental", "outro", "section"]):
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


def _song_name_mention_instruction() -> str:
    return "Do not mention the song name unless the original question explicitly asks for it. "


def _bar_beat_time_instruction() -> str:
    return "When bar and beat facts are available, report time as <bar>.<beat> (<seconds>s), with bar.beat first. "


async def _call_mcp_tool(name: str, arguments: Dict[str, Any]) -> Any:
    async with Client(MCP_BASE_URL) as client:
        result = await client.call_tool(name, arguments, raise_on_error=False)
    if result.is_error:
        detail = None
        if result.content:
            text_value = getattr(result.content[0], "text", None)
            if isinstance(text_value, str):
                detail = text_value
        return {"ok": False, "error": {"code": "mcp_call_failed", "message": detail or f"Tool '{name}' failed"}}
    return result.data if result.data is not None else result.structured_content


async def call_mcp(tool_name: str, args: Dict[str, Any]) -> Any:
    if tool_name not in MCP_TOOL_MAP:
        return {
            "error": "MCP_TOOL_NOT_MAPPED",
            "tool_name": tool_name,
            "available_mappings": list(MCP_TOOL_MAP.keys()),
            "hint": "Call /debug/mcp/tools and map MCP_TOOL_MAP to real tool names."
        }

    if tool_name == "mcp_read_sections":
        song = str(args.get("song") or args.get("song_id") or "")
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], {"song": song} if song else {})

    if tool_name == "mcp_find_section":
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], {"section_name": str(args.get("section_name") or "")})

    if tool_name == "mcp_find_bar_beat":
        song = str(args.get("song") or args.get("song_id") or "")
        payload: Dict[str, Any] = {"bar": int(args.get("bar", 0)), "beat": int(args.get("beat", 0))}
        if song:
            payload["song"] = song
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)

    if tool_name == "mcp_find_chord":
        song = str(args.get("song") or args.get("song_id") or "")
        payload: Dict[str, Any] = {"chord": str(args.get("chord") or ""), "occurrence": int(args.get("occurrence", 1) or 1)}
        if song:
            payload["song"] = song
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)

    if tool_name in {"mcp_read_beats", "mcp_read_chords", "mcp_read_loudness", "mcp_read_bar_beats"}:
        song = str(args.get("song") or args.get("song_id") or "")
        payload = {
            key: value
            for key, value in args.items()
            if key in {"start_time", "end_time", "section", "start_bar", "start_beat", "end_bar", "end_beat"}
        }
        if song:
            payload["song"] = song
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)

    if tool_name == "mcp_read_cue_window":
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], {"start_time": float(args.get("start_time", 0.0)), "end_time": float(args.get("end_time", 0.0))})

    return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], args)


def _format_sections(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    sections = payload.get("sections") or []
    song = payload.get("song") or "unknown"
    if not sections:
        return f"Song: {song}\nSections: unavailable"
    lines = [f"Song: {song}", "Sections:"]
    for section in sections:
        name = section.get("name") or "Unnamed"
        start_time = float(section.get("start_s", 0.0))
        end_time = float(section.get("end_s", 0.0))
        start_bar = section.get("start_bar")
        start_beat = section.get("start_beat")
        end_bar = section.get("end_bar")
        end_beat = section.get("end_beat")
        lines.append(
            f"- {name}: start={start_time:.3f}s ({start_bar}.{start_beat}) end={end_time:.3f}s ({end_bar}.{end_beat})"
        )
    return "\n".join(lines)


def _format_section_match(result: Dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return _format_generic_result(result)
    if not result.get("ok"):
        error = result.get("error") or {}
        return (
            "SECTION_LOOKUP_RESULT\n"
            "section_found=false\n"
            f"error_code={error.get('code', 'unknown')}\n"
            f"error_message={error.get('message', 'unknown')}"
        )
    payload = result.get("data") or {}
    section = payload.get("section") or {}
    return (
        "SECTION_LOOKUP_RESULT\n"
        "section_found=true\n"
        f"song={payload.get('song', 'unknown')}\n"
        f"section_name={section.get('name', 'Unnamed')}\n"
        f"section_start_seconds={float(section.get('start_s', 0.0)):.3f}\n"
        f"section_end_seconds={float(section.get('end_s', 0.0)):.3f}"
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
    return (
        f"Song: {payload.get('song', 'unknown')}\n"
        "Position:\n"
        f"- time={float(position.get('time', 0.0)):.3f}s bar={int(position.get('bar', 0))} beat={int(position.get('beat', 0))} chord={position.get('chord', 'unknown')}"
    )


def _format_chord_match(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    chord = payload.get("chord") or {}
    if not chord:
        return _format_generic_result(result)
    return (
        f"Song: {payload.get('song', 'unknown')}\n"
        "Chord Match:\n"
        f"- occurrence={int(payload.get('occurrence', 1))} time={float(chord.get('time_s', 0.0)):.3f}s bar={int(chord.get('bar', 0))} beat={int(chord.get('beat', 0))} chord={chord.get('label', 'unknown')}"
    )


def _format_chords(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    chords = payload.get("chords") or []
    song = payload.get("song") or "unknown"
    if not chords:
        return f"Song: {song}\nChords: unavailable"
    lines = [f"Song: {song}", "Chords:"]
    for chord in chords[:32]:
        lines.append(
            f"- time={float(chord.get('time_s', 0.0)):.3f}s bar={int(chord.get('bar', 0))} beat={int(chord.get('beat', 0))} chord={chord.get('label', 'unknown')}"
        )
    return "\n".join(lines)


def _format_cue_window(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    entries = payload.get("entries") or []
    lines = [
        f"Cue Window: start={float(payload.get('start_time', 0.0)):.3f}s end={float(payload.get('end_time', 0.0)):.3f}s",
        "Entries:" if entries else "Entries: none",
    ]
    for entry in entries[:64]:
        if entry.get("chaser_id"):
            lines.append(
                f"- time={float(entry.get('time', 0.0)):.3f}s chaser={entry.get('chaser_id')} created_by={entry.get('created_by', 'unknown')}"
            )
        else:
            lines.append(
                f"- time={float(entry.get('time', 0.0)):.3f}s fixture={entry.get('fixture_id')} effect={entry.get('effect')} duration={float(entry.get('duration', 0.0)):.3f}s created_by={entry.get('created_by', 'unknown')}"
            )
    return "\n".join(lines)


def _format_fixtures(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    fixtures = payload.get("fixtures") or []
    if not fixtures:
        return "Fixtures: unavailable"
    lines = ["Fixtures:"]
    for fixture in fixtures[:64]:
        effects = ",".join(fixture.get("supported_effects") or [])
        lines.append(
            f"- id={fixture.get('id')} name={fixture.get('name')} type={fixture.get('type')} supported_effects={effects}"
        )
    return "\n".join(lines)


def _format_pois(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    pois = payload.get("pois") or []
    if not pois:
        return "POIs: unavailable"
    lines = ["POIs:"]
    for poi in pois[:64]:
        lines.append(f"- id={poi.get('id')} name={poi.get('name')}")
    return "\n".join(lines)


def _format_chasers(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    chasers = payload.get("chasers") or []
    if not chasers:
        return "Chasers: unavailable"
    lines = ["Chasers:"]
    for chaser in chasers[:32]:
        lines.append(f"- id={chaser.get('id')} name={chaser.get('name')} description={chaser.get('description')}")
    return "\n".join(lines)


def _format_cursor(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    if not payload:
        return _format_generic_result(result)
    return (
        f"Cursor: time={float(payload.get('time_s', 0.0)):.3f}s bar={payload.get('bar')} beat={payload.get('beat')} "
        f"section={payload.get('section_name')} next={payload.get('next_bar')}.{payload.get('next_beat')}@{payload.get('next_beat_time_s')}s"
    )


def _format_loudness(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    if not payload:
        return orjson.dumps(result).decode("utf-8")
    return (
        f"Song: {payload.get('song', 'unknown')}\n"
        f"Window: start={float(payload.get('start_time', 0.0)):.3f}s end={float(payload.get('end_time', 0.0) or 0.0):.3f}s\n"
        f"Loudness: avg={float(payload.get('average', 0.0)):.6f} min={float(payload.get('minimum', 0.0)):.6f} "
        f"max={float(payload.get('maximum', 0.0)):.6f} samples={int(payload.get('samples', 0))}"
    )


def _format_generic_result(result: Any) -> str:
    return orjson.dumps(result).decode("utf-8")


def _render_tool_result(tool_name: str, result: Any) -> str:
    if not isinstance(result, dict):
        return _format_generic_result(result)
    if not result.get("ok"):
        return _format_generic_result(result)
    if tool_name == "mcp_read_sections":
        return _format_sections(result)
    if tool_name == "mcp_find_section":
        return _format_section_match(result)
    if tool_name == "mcp_read_beats":
        return _format_beats(result)
    if tool_name == "mcp_read_bar_beats":
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
    if tool_name == "mcp_read_pois":
        return _format_pois(result)
    if tool_name == "mcp_read_chasers":
        return _format_chasers(result)
    if tool_name == "mcp_read_cursor":
        return _format_cursor(result)
    if tool_name == "mcp_read_loudness":
        return _format_loudness(result)
    return _format_generic_result(result)


def _build_section_answer_messages(messages: List[Dict[str, Any]], result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            original_question = str(message.get("content") or "")
            break

    if isinstance(result, dict) and result.get("ok"):
        payload = result.get("data") or {}
        section = payload.get("section") or {}
        section_block = (
            "section_found=true\n"
            f"section_name={section.get('name', 'Unnamed')}\n"
            f"section_start_seconds={float(section.get('start_s', 0.0)):.3f}\n"
            f"section_end_seconds={float(section.get('end_s', 0.0)):.3f}"
        )
    else:
        error = (result.get("error") or {}) if isinstance(result, dict) else {}
        section_block = (
            "section_found=false\n"
            f"error_code={error.get('code', 'unknown')}\n"
            f"error_message={error.get('message', 'unknown')}"
        )

    return [
        {
            "role": "system",
            "content": (
                "Answer only from the resolved section facts provided by the user. "
                + _song_name_mention_instruction() +
                _bar_beat_time_instruction() +
                "If section_found=true, never say the data is missing. "
                "Answer the original question directly with the exact numeric time. Use seconds only if bar and beat are unavailable in the resolved facts. "
                "Keep the answer to one sentence."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Original question: {original_question}\n"
                f"Resolved section facts:\n{section_block}\n"
                "Answer the original question directly."
            ),
        },
    ]


def _build_chord_answer_messages(messages: List[Dict[str, Any]], result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    payload = (result.get("data") or {}) if isinstance(result, dict) and result.get("ok") else {}
    chord = payload.get("chord") or {}
    facts = (
        f"occurrence={int(payload.get('occurrence', 1))}\n"
        f"time_seconds={float(chord.get('time_s', 0.0)):.3f}\n"
        f"bar={int(chord.get('bar', 0))}\n"
        f"beat={int(chord.get('beat', 0))}\n"
        f"chord={chord.get('label', 'unknown')}"
    )
    return [
        {
            "role": "system",
            "content": (
                "Answer only from the resolved chord facts provided by the user. "
                + _song_name_mention_instruction() +
                _bar_beat_time_instruction() +
                "Report the exact bar.beat first and the exact seconds in parentheses in one sentence."
            ),
        },
        {
            "role": "user",
            "content": f"Original question: {original_question}\nResolved chord facts:\n{facts}\nAnswer the original question directly.",
        },
    ]


def _build_cursor_answer_messages(messages: List[Dict[str, Any]], result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    payload = (result.get("data") or {}) if isinstance(result, dict) and result.get("ok") else {}
    facts = (
        f"time_seconds={float(payload.get('time_s', 0.0)):.3f}\n"
        f"bar={payload.get('bar')}\n"
        f"beat={payload.get('beat')}\n"
        f"section={payload.get('section_name')}"
    )
    return [
        {
            "role": "system",
            "content": (
                "Answer only from the resolved cursor facts provided by the user. "
                + _song_name_mention_instruction() +
                _bar_beat_time_instruction() +
                "You must report the exact bar.beat first and the exact seconds in parentheses in one sentence, with no reinterpretation."
            ),
        },
        {
            "role": "user",
            "content": f"Original question: {original_question}\nResolved cursor facts:\n{facts}\nAnswer the original question directly.",
        },
    ]


def _is_section_timing_question(messages: List[Dict[str, Any]]) -> bool:
    prompt = _latest_user_prompt(messages).lower()
    if not prompt:
        return False
    if any(token in prompt for token in ["start", "starts", "end", "ends", "begin", "begins"]):
        return True
    if any(token in prompt for token in ["where", "when"]) and any(token in prompt for token in ["intro", "verse", "chorus", "instrumental", "outro", "section"]):
        return True
    return False


def _extract_section_name(prompt: str) -> Optional[str]:
    lowered = str(prompt or "").lower()
    section_names = ["intro", "verse", "chorus", "instrumental", "outro"]
    for section_name in section_names:
        if section_name in lowered:
            return section_name.title()
    for word in re.findall(r"[a-z]+", lowered):
        close_match = difflib.get_close_matches(word, section_names, n=1, cutoff=0.7)
        if close_match:
            return close_match[0].title()
    return None


ORDINAL_WORD_TO_INDEX = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
}


def _extract_section_reference(prompt: str) -> tuple[Optional[str], int]:
    lowered = str(prompt or "").lower()
    match = re.search(
        r"\b(first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)\s+(intro|verse|chorus|instrumental|outro)\b",
        lowered,
    )
    if match:
        raw_ordinal = match.group(1)
        section_name = match.group(2).title()
        occurrence = ORDINAL_WORD_TO_INDEX.get(raw_ordinal)
        if occurrence is None:
            occurrence = int(re.sub(r"(?:st|nd|rd|th)$", "", raw_ordinal))
        return section_name, max(1, occurrence)
    section_name = _extract_section_name(prompt)
    return section_name, 1


def _find_section_occurrence(result: Dict[str, Any], section_name: str, occurrence: int) -> Optional[Dict[str, Any]]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    sections = (result.get("data") or {}).get("sections") or []
    normalized_target = str(section_name or "").strip().lower()
    matches = [
        section
        for section in sections
        if str(section.get("name") or section.get("label") or "").strip().lower() == normalized_target
    ]
    if occurrence <= 0 or occurrence > len(matches):
        return None
    return matches[occurrence - 1]


def _find_previous_beat_time(result: Dict[str, Any], boundary_time: float) -> Optional[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    beats = (result.get("data") or {}).get("beats") or []
    previous_times = [
        float(beat.get("time", 0.0) or 0.0)
        for beat in beats
        if float(beat.get("time", 0.0) or 0.0) < float(boundary_time)
    ]
    if not previous_times:
        return None
    return max(previous_times)


def _resolve_poi_id(prompt: str, result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    lowered = str(prompt or "").lower()
    pois = (result.get("data") or {}).get("pois") or []
    best_match: tuple[int, str] | None = None
    for poi in pois:
        poi_id = str(poi.get("id") or "").strip()
        poi_name = str(poi.get("name") or "").strip()
        for candidate in [poi_name.lower(), poi_id.lower()]:
            if not candidate:
                continue
            if re.search(rf"\b{re.escape(candidate)}\b", lowered):
                score = len(candidate)
                if best_match is None or score > best_match[0]:
                    best_match = (score, poi_id)
    return best_match[1] if best_match is not None else None


def _extract_ordered_poi_ids(prompt: str, result: Dict[str, Any]) -> List[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    lowered = str(prompt or "").lower()
    pois = (result.get("data") or {}).get("pois") or []
    mentions: List[tuple[int, int, str]] = []
    for poi in pois:
        poi_id = str(poi.get("id") or "").strip()
        poi_name = str(poi.get("name") or "").strip()
        if not poi_id:
            continue
        for candidate in [poi_name.lower(), poi_id.lower()]:
            if not candidate:
                continue
            for match in re.finditer(rf"\b{re.escape(candidate)}\b", lowered):
                mentions.append((match.start(), -len(candidate), poi_id))
    ordered_ids: List[str] = []
    for _, _, poi_id in sorted(mentions):
        if poi_id not in ordered_ids:
            ordered_ids.append(poi_id)
    return ordered_ids


def _extract_poi_transition(prompt: str, result: Dict[str, Any]) -> Optional[tuple[str, str, Optional[str]]]:
    poi_ids = _extract_ordered_poi_ids(prompt, result)
    if len(poi_ids) < 2:
        return None
    start_poi, subject_poi = poi_ids[0], poi_ids[1]
    end_poi = poi_ids[2] if len(poi_ids) > 2 else None
    return start_poi, subject_poi, end_poi


def _is_full_cue_clear_request(prompt: str) -> bool:
    lowered = str(prompt or "").lower()
    if re.search(r"\bclear\s+the\s+cue\b", lowered):
        return True
    has_all = any(token in lowered for token in ["all", "entire", "whole", "full"])
    return has_all and "cue" in lowered


def _extract_chord_label(prompt: str) -> Optional[str]:
    match = re.search(r"chord(?:s|\s+is|s\s+is|s\s+turns\s+to|\s+turns\s+to)?\s+(none|N|[A-G](?:#|b)?m?)(?=$|\s|[^A-Za-z0-9_])", str(prompt or ""), flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def _extract_chord_transition(prompt: str) -> Optional[tuple[str, str]]:
    match = re.search(
        r"changes?\s+from\s+([A-G](?:#|b)?m?)(?=\s+to\s+)\s+to\s+([A-G](?:#|b)?m?)(?=$|\s|[^A-Za-z0-9_])",
        str(prompt or ""),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1), match.group(2)


def _extract_effect_name(prompt: str) -> Optional[str]:
    lowered = str(prompt or "").lower()
    for effect_name in ["flash", "strobe", "full", "fade_in"]:
        if effect_name.replace("_", " ") in lowered or effect_name in lowered:
            return effect_name
    return None


def _find_chord_transition_time(result: Dict[str, Any], start_label: str, end_label: str) -> Optional[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    chords = (result.get("data") or {}).get("chords") or []
    start_normalized = _normalize_chord_label(start_label)
    end_normalized = _normalize_chord_label(end_label)
    for current, nxt in zip(chords, chords[1:]):
        current_label = _normalize_chord_label(str(current.get("label") or current.get("chord") or ""))
        next_label = _normalize_chord_label(str(nxt.get("label") or nxt.get("chord") or ""))
        if current_label == start_normalized and next_label == end_normalized:
            return float(nxt.get("time_s", nxt.get("time", 0.0)) or 0.0)
    return None


def _normalize_chord_label(label: str) -> str:
    lowered = str(label or "").strip().lower()
    if lowered in {"n", "none", "no chord", "no_chord"}:
        return "n"
    return lowered


def _resolve_prism_fixture_ids(result: Dict[str, Any]) -> List[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    fixtures = (result.get("data") or {}).get("fixtures") or []
    ids = [str(fixture.get("id") or "") for fixture in fixtures if "prism" in str(fixture.get("id") or "").lower()]
    return [fixture_id for fixture_id in ids if fixture_id]


def _resolve_left_prism_fixture_ids(result: Dict[str, Any]) -> List[str]:
    return [fixture_id for fixture_id in _resolve_prism_fixture_ids(result) if fixture_id.endswith("_l")]


def _resolve_right_prism_fixture_ids(result: Dict[str, Any]) -> List[str]:
    return [fixture_id for fixture_id in _resolve_prism_fixture_ids(result) if fixture_id.endswith("_r")]


def _resolve_target_prism_fixture_ids(prompt: str, result: Dict[str, Any]) -> List[str]:
    lowered = str(prompt or "").lower()
    if "right" in lowered:
        return _resolve_right_prism_fixture_ids(result)
    if "left" in lowered:
        return _resolve_left_prism_fixture_ids(result)
    return _resolve_prism_fixture_ids(result)


def _resolve_parcan_fixture_ids(result: Dict[str, Any]) -> List[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    fixtures = (result.get("data") or {}).get("fixtures") or []
    ids = [str(fixture.get("id") or "") for fixture in fixtures if str(fixture.get("id") or "").lower().startswith("parcan")]
    return [fixture_id for fixture_id in ids if fixture_id]


def _resolve_proton_fixture_ids(result: Dict[str, Any]) -> List[str]:
    return [fixture_id for fixture_id in _resolve_parcan_fixture_ids(result) if fixture_id.endswith(("_pl", "_pr"))]


def _resolve_non_parcan_fixture_ids(result: Dict[str, Any]) -> List[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    fixtures = (result.get("data") or {}).get("fixtures") or []
    ids = [str(fixture.get("id") or "") for fixture in fixtures if not str(fixture.get("id") or "").lower().startswith("parcan")]
    return [fixture_id for fixture_id in ids if fixture_id]


def _find_chord_times(result: Dict[str, Any], chord_label: str) -> List[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    chords = (result.get("data") or {}).get("chords") or []
    label_normalized = _normalize_chord_label(chord_label)
    return [
        float(chord.get("time_s", chord.get("time", 0.0)) or 0.0)
        for chord in chords
        if _normalize_chord_label(str(chord.get("label") or chord.get("chord") or "")) == label_normalized
    ]


def _find_chord_spans(result: Dict[str, Any], chord_label: str) -> List[tuple[float, float]]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    chords = (result.get("data") or {}).get("chords") or []
    label_normalized = _normalize_chord_label(chord_label)
    spans: List[tuple[float, float]] = []
    index = 0
    while index < len(chords):
        current_label = _normalize_chord_label(str(chords[index].get("label") or chords[index].get("chord") or ""))
        if current_label != label_normalized:
            index += 1
            continue
        start_time = float(chords[index].get("time_s", chords[index].get("time", 0.0)) or 0.0)
        next_index = index + 1
        while next_index < len(chords):
            next_label = _normalize_chord_label(str(chords[next_index].get("label") or chords[next_index].get("chord") or ""))
            if next_label != label_normalized:
                spans.append((start_time, float(chords[next_index].get("time_s", chords[next_index].get("time", 0.0)) or start_time)))
                break
            next_index += 1
        index = next_index
    return [span for span in spans if span[1] > span[0]]


def _extract_color_name(prompt: str) -> Optional[str]:
    lowered = str(prompt or "").lower()
    for color_name in ["blue", "red", "green", "white", "yellow", "cyan", "magenta", "purple", "orange", "pink"]:
        if re.search(rf"\b{re.escape(color_name)}\b", lowered):
            return color_name
    return None


def _color_name_to_rgb(color_name: str) -> Optional[Dict[str, int]]:
    return {
        "blue": {"red": 0, "green": 0, "blue": 255},
        "red": {"red": 255, "green": 0, "blue": 0},
        "green": {"red": 0, "green": 255, "blue": 0},
        "white": {"red": 255, "green": 255, "blue": 255},
        "yellow": {"red": 255, "green": 255, "blue": 0},
        "cyan": {"red": 0, "green": 255, "blue": 255},
        "magenta": {"red": 255, "green": 0, "blue": 255},
        "purple": {"red": 128, "green": 0, "blue": 255},
        "orange": {"red": 255, "green": 128, "blue": 0},
        "pink": {"red": 255, "green": 105, "blue": 180},
    }.get(color_name.lower())


def _describe_cue_add_entries(entries: List[Dict[str, Any]]) -> str:
    fixtures = ", ".join(dict.fromkeys(str(entry.get("fixture_id") or "") for entry in entries if str(entry.get("fixture_id") or "")))
    unique_times = list(dict.fromkeys(float(entry.get("time", 0.0) or 0.0) for entry in entries))
    if len(unique_times) <= 1:
        time_text = f"{(unique_times[0] if unique_times else 0.0):.3f}s"
    else:
        time_text = ", ".join(f"{time_value:.3f}s" for time_value in unique_times)
    if entries:
        first_effect = str(entries[0].get("effect") or "effect")
        if first_effect == "blackout":
            return f"Turn off {fixtures} at {time_text}."
        if first_effect == "fade_out":
            return f"Add fade_out to {fixtures} at {time_text}."
        first_data = entries[0].get("data") or {}
        if first_effect == "move_to_poi":
            target_poi = str(first_data.get("target_POI") or first_data.get("poi") or first_data.get("POI") or "").strip()
            if target_poi:
                return f"Move {fixtures} to {target_poi} at {time_text}."
        if first_effect == "seek":
            start_poi = str(first_data.get("start_POI") or "").strip()
            subject_poi = str(first_data.get("subject_POI") or "").strip()
            if start_poi and subject_poi:
                return f"Add seek on {fixtures} from {start_poi} to {subject_poi} at {time_text}."
        if first_effect == "sweep":
            start_poi = str(first_data.get("start_POI") or "").strip()
            subject_poi = str(first_data.get("subject_POI") or "").strip()
            end_poi = str(first_data.get("end_POI") or "").strip()
            if start_poi and subject_poi and end_poi:
                return f"Add sweep on {fixtures} from {start_poi} through {subject_poi} to {end_poi} at {time_text}."
            if start_poi and subject_poi:
                return f"Add sweep on {fixtures} from {start_poi} through {subject_poi} at {time_text}."
        if first_effect == "full":
            for color_name, rgb in {
                "blue": {"red": 0, "green": 0, "blue": 255},
                "red": {"red": 255, "green": 0, "blue": 0},
                "green": {"red": 0, "green": 255, "blue": 0},
                "white": {"red": 255, "green": 255, "blue": 255},
                "yellow": {"red": 255, "green": 255, "blue": 0},
                "cyan": {"red": 0, "green": 255, "blue": 255},
                "magenta": {"red": 255, "green": 0, "blue": 255},
                "purple": {"red": 128, "green": 0, "blue": 255},
                "orange": {"red": 255, "green": 128, "blue": 0},
                "pink": {"red": 255, "green": 105, "blue": 180},
            }.items():
                if all(int(first_data.get(channel, -1)) == value for channel, value in rgb.items()):
                    return f"Set {fixtures} to {color_name} at {time_text}."
    effect_name = str(entries[0].get("effect") or "effect") if entries else "effect"
    return f"Add {effect_name} to {fixtures} at {time_text}."


def _section_start_times(result: Dict[str, Any]) -> List[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    sections = (result.get("data") or {}).get("sections") or []
    return [float(section.get("start_s", 0.0) or 0.0) for section in sections]


def _extract_bar_beat(prompt: str) -> Optional[tuple[int, int]]:
    match = re.search(r"bar\s+(\d+)(?:[\.:](\d+))?", str(prompt or ""), flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2) or 1)


def _build_first_effect_answer_messages(messages: List[Dict[str, Any]], section_result: Dict[str, Any], cue_result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    section = ((section_result.get("data") or {}).get("section") or {}) if section_result.get("ok") else {}
    entries = ((cue_result.get("data") or {}).get("entries") or []) if cue_result.get("ok") else []
    effect_entries = [entry for entry in entries if entry.get("fixture_id") and entry.get("effect")]
    earliest_time = min(float(entry.get("time", 0.0)) for entry in effect_entries)
    earliest_entries = [entry for entry in effect_entries if float(entry.get("time", 0.0)) == earliest_time]
    fixtures = ", ".join(str(entry.get("fixture_id")) for entry in earliest_entries)
    effect = str(earliest_entries[0].get("effect") or "") if earliest_entries else ""
    duration = float(earliest_entries[0].get("duration", 0.0)) if earliest_entries else 0.0
    facts = (
        f"section_name={section.get('name', 'unknown')}\n"
        f"section_start_seconds={float(section.get('start_s', 0.0)):.3f}\n"
        f"first_effect_time_seconds={earliest_time:.3f}\n"
        f"fixtures={fixtures}\n"
        f"effect={effect}\n"
        f"duration_seconds={duration:.3f}"
    )
    return [
        {
            "role": "system",
            "content": "Answer only from the resolved section and cue facts provided by the user. " + _song_name_mention_instruction() + _bar_beat_time_instruction() + "If bar and beat for the first effect are unavailable in the resolved facts, use seconds. Use exactly one sentence in this structure: At <bar>.<beat> (<first_effect_time_seconds>s), <fixtures> <effect> for <duration_seconds>s. If bar and beat are unavailable, use: At <first_effect_time_seconds>s, <fixtures> <effect> for <duration_seconds>s.",
        },
        {
            "role": "user",
            "content": f"Original question: {original_question}\nResolved facts:\n{facts}\nAnswer the original question directly.",
        },
    ]


def _build_loudness_answer_messages(messages: List[Dict[str, Any]], loudness_result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    payload = (loudness_result.get("data") or {}) if loudness_result.get("ok") else {}
    facts = (
        f"start_time={float(payload.get('start_time', 0.0)):.3f}\n"
        f"end_time={float(payload.get('end_time', 0.0)):.3f}\n"
        f"average={float(payload.get('average', 0.0)):.6f}\n"
        f"minimum={float(payload.get('minimum', 0.0)):.6f}\n"
        f"maximum={float(payload.get('maximum', 0.0)):.6f}"
    )
    return [
        {
            "role": "system",
            "content": "Answer only from the resolved loudness facts provided by the user. " + _song_name_mention_instruction() + _bar_beat_time_instruction() + "If bar and beat facts are unavailable for the time range, use seconds. Use exactly one sentence in this structure: The first verse spans <start_bar>.<start_beat> (<start_time>s) to <end_bar>.<end_beat> (<end_time>s) and has average loudness <average>. If bar and beat are unavailable, use seconds only.",
        },
        {
            "role": "user",
            "content": f"Original question: {original_question}\nResolved loudness facts:\n{facts}\nAnswer the original question directly.",
        },
    ]


def _build_fixtures_at_bar_answer_messages(messages: List[Dict[str, Any]], position_result: Dict[str, Any], cue_result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    position = ((position_result.get("data") or {}).get("position") or {}) if position_result.get("ok") else {}
    entries = ((cue_result.get("data") or {}).get("entries") or []) if cue_result.get("ok") else []
    effect_entries = [entry for entry in entries if entry.get("fixture_id") and entry.get("effect")]
    fixtures = ", ".join(str(entry.get("fixture_id")) for entry in effect_entries)
    effect = str(effect_entries[0].get("effect") or "") if effect_entries else ""
    duration = float(effect_entries[0].get("duration", 0.0)) if effect_entries else 0.0
    facts = (
        f"time_seconds={float(position.get('time', 0.0)):.3f}\n"
        f"bar={int(position.get('bar', 0))}\n"
        f"beat={int(position.get('beat', 0))}\n"
        f"fixtures={fixtures}\n"
        f"effect={effect}\n"
        f"duration_seconds={duration:.3f}"
    )
    return [
        {
            "role": "system",
            "content": "Answer only from the resolved musical position and cue facts provided by the user. " + _song_name_mention_instruction() + _bar_beat_time_instruction() + "Use exactly one sentence in this structure: At <bar>.<beat> (<time_seconds>s), <fixtures> <effect> for <duration_seconds>s.",
        },
        {
            "role": "user",
            "content": f"Original question: {original_question}\nResolved facts:\n{facts}\nAnswer the original question directly.",
        },
    ]


def _build_left_fixtures_answer_messages(messages: List[Dict[str, Any]], fixtures_result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    fixtures = ((fixtures_result.get("data") or {}).get("fixtures") or []) if fixtures_result.get("ok") else []
    left_ids = [str(fixture.get("id")) for fixture in fixtures if str(fixture.get("id") or "").endswith(("_l", "_pl"))]
    facts = "left_fixture_ids=" + ", ".join(left_ids)
    return [
        {
            "role": "system",
            "content": "Answer only from the resolved fixture facts provided by the user. " + _song_name_mention_instruction() + "Repeat every id from left_fixture_ids exactly once, comma-separated, with no omissions.",
        },
        {
            "role": "user",
            "content": f"Original question: {original_question}\nResolved fixture facts:\n{facts}\nAnswer the original question directly.",
        },
    ]


async def _run_stream_fast_path(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    prompt = _latest_user_prompt(messages)
    lowered = prompt.lower()
    section_name, section_occurrence = _extract_section_reference(prompt)
    used_tools: List[str] = []

    if any(word in lowered for word in ["move", "point", "aim"]) and "prism" in lowered and "one beat before" in lowered and section_name:
        used_tools.append("mcp_read_sections")
        sections_result = await call_mcp("mcp_read_sections", {})
        used_tools.append("mcp_read_fixtures")
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        used_tools.append("mcp_read_pois")
        pois_result = await call_mcp("mcp_read_pois", {})
        section = _find_section_occurrence(sections_result, section_name, section_occurrence)
        poi_id = _resolve_poi_id(prompt, pois_result)
        if section is not None and poi_id:
            fixture_ids = _resolve_target_prism_fixture_ids(prompt, fixtures_result)
            if fixture_ids:
                section_start = float(section.get("start_s", 0.0) or 0.0)
                used_tools.append("mcp_read_beats")
                beats_result = await call_mcp("mcp_read_beats", {"end_time": section_start})
                cue_time = _find_previous_beat_time(beats_result, section_start)
                if cue_time is not None:
                    duration = max(0.1, round(section_start - cue_time, 3))
                    return {
                        "used_tools": used_tools,
                        "proposal": _proposal_for_tool(
                            "propose_cue_add_entries",
                            {
                                "entries": [
                                    {
                                        "time": cue_time,
                                        "fixture_id": fixture_id,
                                        "effect": "move_to_poi",
                                        "duration": duration,
                                        "data": {"target_POI": poi_id},
                                    }
                                    for fixture_id in fixture_ids
                                ]
                            },
                        ),
                    }

    if any(word in lowered for word in ["seek", "sweep"]) and "prism" in lowered and "one beat before" in lowered and section_name:
        effect_name = "seek" if "seek" in lowered else "sweep"
        used_tools.append("mcp_read_sections")
        sections_result = await call_mcp("mcp_read_sections", {})
        used_tools.append("mcp_read_fixtures")
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        used_tools.append("mcp_read_pois")
        pois_result = await call_mcp("mcp_read_pois", {})
        section = _find_section_occurrence(sections_result, section_name, section_occurrence)
        poi_transition = _extract_poi_transition(prompt, pois_result)
        if section is not None and poi_transition is not None:
            fixture_ids = _resolve_target_prism_fixture_ids(prompt, fixtures_result)
            if fixture_ids:
                section_start = float(section.get("start_s", 0.0) or 0.0)
                used_tools.append("mcp_read_beats")
                beats_result = await call_mcp("mcp_read_beats", {"end_time": section_start})
                cue_time = _find_previous_beat_time(beats_result, section_start)
                if cue_time is not None:
                    start_poi, subject_poi, end_poi = poi_transition
                    duration = max(0.1, round(section_start - cue_time, 3))
                    data: Dict[str, Any] = {"start_POI": start_poi, "subject_POI": subject_poi}
                    if effect_name == "sweep" and end_poi:
                        data["end_POI"] = end_poi
                    return {
                        "used_tools": used_tools,
                        "proposal": _proposal_for_tool(
                            "propose_cue_add_entries",
                            {
                                "entries": [
                                    {
                                        "time": cue_time,
                                        "fixture_id": fixture_id,
                                        "effect": effect_name,
                                        "duration": duration,
                                        "data": dict(data),
                                    }
                                    for fixture_id in fixture_ids
                                ]
                            },
                        ),
                    }

    if any(word in lowered for word in ["flash", "effect", "add"]) and "each section" in lowered and "prism" in lowered:
        effect_name = _extract_effect_name(prompt)
        if effect_name is not None:
            used_tools.append("mcp_read_sections")
            sections_result = await call_mcp("mcp_read_sections", {})
            used_tools.append("mcp_read_fixtures")
            fixtures_result = await call_mcp("mcp_read_fixtures", {})
            section_times = _section_start_times(sections_result)
            fixture_ids = _resolve_left_prism_fixture_ids(fixtures_result) if "left" in lowered else _resolve_prism_fixture_ids(fixtures_result)
            if section_times and fixture_ids:
                return {
                    "used_tools": used_tools,
                    "proposal": _proposal_for_tool(
                        "propose_cue_add_entries",
                        {
                            "entries": [
                                {
                                    "time": section_time,
                                    "fixture_id": fixture_id,
                                    "effect": effect_name,
                                    "duration": 0.5,
                                    "data": {},
                                }
                                for section_time in section_times
                                for fixture_id in fixture_ids
                            ]
                        },
                    ),
                }

    if any(word in lowered for word in ["add", "apply"]) and "prism" in lowered and "change" in lowered:
        chord_transition = _extract_chord_transition(prompt)
        effect_name = _extract_effect_name(prompt)
        if chord_transition is not None and effect_name is not None:
            start_chord, end_chord = chord_transition
            used_tools.append("mcp_read_chords")
            chords_result = await call_mcp("mcp_read_chords", {})
            used_tools.append("mcp_read_fixtures")
            fixtures_result = await call_mcp("mcp_read_fixtures", {})
            transition_time = _find_chord_transition_time(chords_result, start_chord, end_chord)
            prism_fixture_ids = _resolve_prism_fixture_ids(fixtures_result)
            if transition_time is not None and prism_fixture_ids:
                return {
                    "used_tools": used_tools,
                    "proposal": _proposal_for_tool(
                        "propose_cue_add_entries",
                        {
                            "entries": [
                                {
                                    "time": transition_time,
                                    "fixture_id": fixture_id,
                                    "effect": effect_name,
                                    "duration": 0.5,
                                    "data": {},
                                }
                                for fixture_id in prism_fixture_ids
                            ]
                        },
                    ),
                }

    if any(word in lowered for word in ["set", "make", "turn"]) and "parcan" in lowered and "chord" in lowered:
        chord_label = _extract_chord_label(prompt)
        color_name = _extract_color_name(prompt)
        rgb = _color_name_to_rgb(color_name) if color_name is not None else None
        if chord_label and rgb is not None:
            used_tools.append("mcp_read_chords")
            chords_result = await call_mcp("mcp_read_chords", {})
            used_tools.append("mcp_read_fixtures")
            fixtures_result = await call_mcp("mcp_read_fixtures", {})
            chord_times = _find_chord_times(chords_result, chord_label)
            parcan_fixture_ids = _resolve_parcan_fixture_ids(fixtures_result)
            if chord_times and parcan_fixture_ids:
                return {
                    "used_tools": used_tools,
                    "proposal": _proposal_for_tool(
                        "propose_cue_add_entries",
                        {
                            "entries": [
                                {
                                    "time": chord_time,
                                    "fixture_id": fixture_id,
                                    "effect": "full",
                                    "duration": 0.0,
                                    "data": dict(rgb),
                                }
                                for chord_time in chord_times
                                for fixture_id in parcan_fixture_ids
                            ]
                        },
                    ),
                }

    if any(word in lowered for word in ["set", "make", "turn"]) and "proton" in lowered and "chord" in lowered:
        chord_label = _extract_chord_label(prompt)
        color_name = _extract_color_name(prompt)
        rgb = _color_name_to_rgb(color_name) if color_name is not None else None
        if chord_label and rgb is not None:
            used_tools.append("mcp_read_chords")
            chords_result = await call_mcp("mcp_read_chords", {})
            used_tools.append("mcp_read_fixtures")
            fixtures_result = await call_mcp("mcp_read_fixtures", {})
            chord_times = _find_chord_times(chords_result, chord_label)
            proton_fixture_ids = _resolve_proton_fixture_ids(fixtures_result)
            if chord_times and proton_fixture_ids:
                return {
                    "used_tools": used_tools,
                    "proposal": _proposal_for_tool(
                        "propose_cue_add_entries",
                        {
                            "entries": [
                                {
                                    "time": chord_time,
                                    "fixture_id": fixture_id,
                                    "effect": "full",
                                    "duration": 0.0,
                                    "data": dict(rgb),
                                }
                                for chord_time in chord_times
                                for fixture_id in proton_fixture_ids
                            ]
                        },
                    ),
                }

    if ("turn off" in lowered or "off" in lowered) and "proton" in lowered and "chord" in lowered:
        chord_label = _extract_chord_label(prompt)
        if chord_label:
            used_tools.append("mcp_read_chords")
            chords_result = await call_mcp("mcp_read_chords", {})
            used_tools.append("mcp_read_fixtures")
            fixtures_result = await call_mcp("mcp_read_fixtures", {})
            chord_times = _find_chord_times(chords_result, chord_label)
            proton_fixture_ids = _resolve_proton_fixture_ids(fixtures_result)
            if chord_times and proton_fixture_ids:
                return {
                    "used_tools": used_tools,
                    "proposal": _proposal_for_tool(
                        "propose_cue_add_entries",
                        {
                            "entries": [
                                {
                                    "time": chord_time,
                                    "fixture_id": fixture_id,
                                    "effect": "blackout",
                                    "duration": 0.0,
                                    "data": {},
                                }
                                for chord_time in chord_times
                                for fixture_id in proton_fixture_ids
                            ]
                        },
                    ),
                }

    if "none" in lowered and "prism" in lowered and ("fade out" in lowered or "from 1 to 0" in lowered):
        used_tools.append("mcp_read_chords")
        chords_result = await call_mcp("mcp_read_chords", {})
        used_tools.append("mcp_read_fixtures")
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        none_spans = _find_chord_spans(chords_result, "none")
        prism_fixture_ids = _resolve_prism_fixture_ids(fixtures_result)
        if none_spans and prism_fixture_ids:
            return {
                "used_tools": used_tools,
                "proposal": _proposal_for_tool(
                    "propose_cue_add_entries",
                    {
                        "entries": [
                            {
                                "time": start_time,
                                "fixture_id": fixture_id,
                                    "effect": "fade_out",
                                "duration": max(0.1, end_time - start_time),
                                    "data": {},
                            }
                            for start_time, end_time in none_spans
                            for fixture_id in prism_fixture_ids
                        ]
                    },
                ),
            }

    if "none" in lowered and "fixture" in lowered and ("turn off" in lowered or "off" in lowered):
        used_tools.append("mcp_read_chords")
        chords_result = await call_mcp("mcp_read_chords", {})
        used_tools.append("mcp_read_fixtures")
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        none_spans = _find_chord_spans(chords_result, "none")
        parcan_fixture_ids = _resolve_parcan_fixture_ids(fixtures_result)
        dimmable_fixture_ids = _resolve_non_parcan_fixture_ids(fixtures_result)
        if none_spans and (parcan_fixture_ids or dimmable_fixture_ids):
            entries = [
                {
                    "time": start_time,
                    "fixture_id": fixture_id,
                    "effect": "blackout",
                    "duration": 0.0,
                    "data": {},
                }
                for start_time, _end_time in none_spans
                for fixture_id in parcan_fixture_ids
            ]
            entries.extend(
                {
                    "time": start_time,
                    "fixture_id": fixture_id,
                    "effect": "fade_out",
                    "duration": max(0.1, end_time - start_time),
                    "data": {},
                }
                for start_time, end_time in none_spans
                for fixture_id in dimmable_fixture_ids
            )
            return {
                "used_tools": used_tools,
                "proposal": _proposal_for_tool("propose_cue_add_entries", {"entries": entries}),
            }

    if "first occurrence" in lowered and "chord" in lowered:
        chord_label = _extract_chord_label(prompt)
        if chord_label:
            used_tools.append("mcp_find_chord")
            chord_result = await call_mcp("mcp_find_chord", {"chord": chord_label, "occurrence": 1})
            if isinstance(chord_result, dict) and chord_result.get("ok"):
                return {"used_tools": used_tools, "answer_messages": _build_chord_answer_messages(messages, chord_result)}

    if "cursor" in lowered:
        used_tools.append("mcp_read_cursor")
        cursor_result = await call_mcp("mcp_read_cursor", {})
        if isinstance(cursor_result, dict) and cursor_result.get("ok"):
            return {"used_tools": used_tools, "answer_messages": _build_cursor_answer_messages(messages, cursor_result)}

    if "first effect" in lowered and section_name:
        used_tools.append("mcp_find_section")
        section_result = await call_mcp("mcp_find_section", {"section_name": section_name})
        section = ((section_result.get("data") or {}).get("section") or {}) if isinstance(section_result, dict) else {}
        if section:
            used_tools.append("mcp_read_cue_window")
            cue_result = await call_mcp(
                "mcp_read_cue_window",
                {"start_time": float(section.get("start_s", 0.0)), "end_time": float(section.get("end_s", 0.0))},
            )
            entries = ((cue_result.get("data") or {}).get("entries") or []) if isinstance(cue_result, dict) else []
            if entries:
                return {"used_tools": used_tools, "answer_messages": _build_first_effect_answer_messages(messages, section_result, cue_result)}

    if "clear" in lowered and "cue" in lowered and _is_full_cue_clear_request(prompt):
        return {
            "used_tools": used_tools,
            "proposal": _proposal_for_tool("propose_cue_clear_all", {}),
        }

    if "clear" in lowered and "cue" in lowered and section_name:
        used_tools.append("mcp_find_section")
        section_result = await call_mcp("mcp_find_section", {"section_name": section_name})
        section = ((section_result.get("data") or {}).get("section") or {}) if isinstance(section_result, dict) else {}
        if section:
            return {
                "used_tools": used_tools,
                "proposal": _proposal_for_tool(
                    "propose_cue_clear_range",
                    {"start_time": float(section.get("start_s", 0.0)), "end_time": float(section.get("end_s", 0.0))},
                ),
            }

    if "loud" in lowered and section_name:
        used_tools.append("mcp_read_loudness")
        loudness_result = await call_mcp("mcp_read_loudness", {"section": section_name})
        if isinstance(loudness_result, dict) and loudness_result.get("ok"):
            return {"used_tools": used_tools, "answer_messages": _build_loudness_answer_messages(messages, loudness_result)}

    if "fixture" in lowered and "bar" in lowered:
        position = _extract_bar_beat(prompt)
        if position is not None:
            bar, beat = position
            used_tools.append("mcp_find_bar_beat")
            position_result = await call_mcp("mcp_find_bar_beat", {"bar": bar, "beat": beat})
            resolved = ((position_result.get("data") or {}).get("position") or {}) if isinstance(position_result, dict) else {}
            if resolved:
                used_tools.append("mcp_read_cue_window")
                cue_result = await call_mcp(
                    "mcp_read_cue_window",
                    {"start_time": float(resolved.get("time", 0.0)), "end_time": float(resolved.get("time", 0.0))},
                )
                entries = ((cue_result.get("data") or {}).get("entries") or []) if isinstance(cue_result, dict) else []
                if entries:
                    return {"used_tools": used_tools, "answer_messages": _build_fixtures_at_bar_answer_messages(messages, position_result, cue_result)}

    if "fixture" in lowered and "left" in lowered:
        used_tools.append("mcp_read_fixtures")
        fixtures_result = await call_mcp("mcp_read_fixtures", {})
        if isinstance(fixtures_result, dict) and fixtures_result.get("ok"):
            return {"used_tools": used_tools, "answer_messages": _build_left_fixtures_answer_messages(messages, fixtures_result)}

    if "chaser" in lowered and "parcan" in lowered and section_name:
        used_tools.append("mcp_find_section")
        section_result = await call_mcp("mcp_find_section", {"section_name": section_name})
        section = ((section_result.get("data") or {}).get("section") or {}) if isinstance(section_result, dict) else {}
        if section:
            used_tools.append("mcp_read_beats")
            beats_result = await call_mcp(
                "mcp_read_beats",
                {"start_time": float(section.get("start_s", 0.0)), "end_time": float(section.get("end_s", 0.0))},
            )
            beat_count = int(((beats_result.get("data") or {}).get("count") or 0)) if isinstance(beats_result, dict) else 0
            repetitions = max(1, beat_count // 4)
            return {
                "used_tools": used_tools,
                "proposal": _proposal_for_tool(
                    "propose_chaser_apply",
                    {"chaser_id": "parcan_left_to_right", "start_time": float(section.get("start_s", 0.0)), "repetitions": repetitions},
                ),
            }

    return None


def _proposal_for_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "propose_cue_add_entries":
        entries = list(args.get("entries") or [])
        return {
            "type": "proposal",
            "action_id": f"proposal-{abs(hash(orjson.dumps(args).decode('utf-8'))) % 1000000}",
            "tool_name": tool_name,
            "arguments": {"entries": entries},
            "title": "Confirm cue add",
            "summary": _describe_cue_add_entries(entries),
        }
    if tool_name == "propose_cue_clear_all":
        return {
            "type": "proposal",
            "action_id": f"proposal-{abs(hash(orjson.dumps(args).decode('utf-8'))) % 1000000}",
            "tool_name": tool_name,
            "arguments": {},
            "title": "Confirm cue sheet clear",
            "summary": "Remove all cue items from the cue sheet.",
        }
    if tool_name == "propose_cue_clear_range":
        start_time = float(args.get("start_time", 0.0))
        end_time = float(args.get("end_time", 0.0))
        return {
            "type": "proposal",
            "action_id": f"proposal-{abs(hash(orjson.dumps(args).decode('utf-8'))) % 1000000}",
            "tool_name": tool_name,
            "arguments": args,
            "title": "Confirm cue clear",
            "summary": f"Remove cue items from {start_time:.3f}s to {end_time:.3f}s.",
        }
    return {
        "type": "proposal",
        "action_id": f"proposal-{abs(hash(orjson.dumps(args).decode('utf-8'))) % 1000000}",
        "tool_name": tool_name,
        "arguments": args,
        "title": "Confirm chaser apply",
        "summary": f"Apply chaser {args.get('chaser_id')} at {float(args.get('start_time', 0.0)):.3f}s for {int(args.get('repetitions', 1))} repetitions.",
    }


def _chunk_text(content: str, chunk_size: int = 48) -> List[str]:
    return [content[index:index + chunk_size] for index in range(0, len(content), chunk_size)] or [""]


async def _llm_complete(client: httpx.AsyncClient, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload)
    response.raise_for_status()
    return response.json()


async def _event_stream(req: ChatRequest):
    request_messages = _inject_query_guidance(req.messages)
    payload = {
        "model": req.model or "local",
        "messages": request_messages,
        "temperature": req.temperature if req.temperature is not None else 0.2,
        "tools": TOOLS,
        "tool_choice": req.tool_choice if req.tool_choice is not None else "auto",
    }

    async with httpx.AsyncClient(timeout=240.0) as client:
        yield f"data: {orjson.dumps({'type': 'status', 'phase': 'thinking', 'label': 'Thinking'}).decode('utf-8')}\n\n"
        fast_path = await _run_stream_fast_path(request_messages)
        if fast_path is not None:
            yield f"data: {orjson.dumps({'type': 'status', 'phase': 'awaiting_tool_calls', 'label': 'Resolving tool calls'}).decode('utf-8')}\n\n"
            for tool_name in fast_path.get("used_tools") or []:
                yield f"data: {orjson.dumps({'type': 'status', 'phase': 'executing_tool', 'label': f'Executing {MCP_TOOL_MAP.get(tool_name, tool_name)}', 'tool_name': tool_name}).decode('utf-8')}\n\n"
            proposal = fast_path.get("proposal")
            if proposal is not None:
                yield f"data: {orjson.dumps(proposal).decode('utf-8')}\n\n"
                yield f"data: {orjson.dumps({'type': 'status', 'phase': 'awaiting_confirmation', 'label': 'Awaiting confirmation'}).decode('utf-8')}\n\n"
                yield "data: [DONE]\n\n"
                return
            answer_messages = fast_path.get("answer_messages") or []
            yield f"data: {orjson.dumps({'type': 'status', 'phase': 'calling_model', 'label': 'Calling local model'}).decode('utf-8')}\n\n"
            data = await _llm_complete(client, {**payload, 'messages': answer_messages, 'tools': [], 'tool_choice': 'none'})
            content = str(data['choices'][0]['message'].get('content') or '')
            for chunk in _chunk_text(content):
                if chunk:
                    yield f"data: {orjson.dumps({'type': 'delta', 'delta': chunk}).decode('utf-8')}\n\n"
            yield f"data: {orjson.dumps({'type': 'done', 'finish_reason': data['choices'][0].get('finish_reason', 'stop')}).decode('utf-8')}\n\n"
            yield "data: [DONE]\n\n"
            return
        messages = list(request_messages)
        while True:
            yield f"data: {orjson.dumps({'type': 'status', 'phase': 'calling_model', 'label': 'Calling local model'}).decode('utf-8')}\n\n"
            data = await _llm_complete(client, {**payload, "messages": messages})
            msg = data["choices"][0]["message"]
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                content = str(msg.get("content") or "")
                for chunk in _chunk_text(content):
                    if chunk:
                        yield f"data: {orjson.dumps({'type': 'delta', 'delta': chunk}).decode('utf-8')}\n\n"
                yield f"data: {orjson.dumps({'type': 'done', 'finish_reason': data['choices'][0].get('finish_reason', 'stop')}).decode('utf-8')}\n\n"
                break

            messages = messages + [msg]
            yield f"data: {orjson.dumps({'type': 'status', 'phase': 'awaiting_tool_calls', 'label': 'Resolving tool calls'}).decode('utf-8')}\n\n"
            tool_messages = []
            section_lookup_result = None
            chord_lookup_result = None
            cursor_lookup_result = None
            write_proposal = None
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                raw_args = tc["function"].get("arguments", "{}")
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                if tool_name.startswith("propose_"):
                    write_proposal = _proposal_for_tool(tool_name, args)
                    break
                yield f"data: {orjson.dumps({'type': 'status', 'phase': 'executing_tool', 'label': f'Executing {MCP_TOOL_MAP.get(tool_name, tool_name)}', 'tool_name': tool_name}).decode('utf-8')}\n\n"
                result = await call_mcp(tool_name, args)
                if tool_name == "mcp_find_section":
                    section_lookup_result = result
                if tool_name == "mcp_find_chord":
                    chord_lookup_result = result
                if tool_name == "mcp_read_cursor":
                    cursor_lookup_result = result
                tool_messages.append({"role": "tool", "tool_call_id": tc["id"], "content": _render_tool_result(tool_name, result)})
            if write_proposal is not None:
                yield f"data: {orjson.dumps(write_proposal).decode('utf-8')}\n\n"
                break
            if section_lookup_result is not None and _is_section_timing_question(messages):
                messages = _build_section_answer_messages(messages, section_lookup_result)
                continue
            if chord_lookup_result is not None:
                messages = _build_chord_answer_messages(messages, chord_lookup_result)
                continue
            if cursor_lookup_result is not None:
                messages = _build_cursor_answer_messages(messages, cursor_lookup_result)
                continue
            messages = messages + tool_messages + [{
                "role": "system",
                "content": (
                    "Answer strictly from the tool outputs already provided in this conversation. "
                    "Do not mention the song name unless the original question explicitly asks for it. "
                    "Do not say that you lack access to databases, metadata, websites, or external tools. "
                    "Use exact values present in the tool outputs, including times, bars, beats, fixture ids, cue effects, and loudness statistics. "
                    "When both bar.beat and seconds are available, present bar.beat first and seconds in parentheses. "
                    "If the requested fact is present in the tool outputs, answer directly with that fact. "
                    "If it is not present, say that the current loaded song data does not contain that fact."
                ),
            }]

    yield "data: [DONE]\n\n"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/debug/mcp/tools")
async def debug_mcp_tools():
    try:
        async with Client(MCP_BASE_URL) as client:
            tools = await client.list_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": getattr(tool, "inputSchema", None),
                }
                for tool in tools
            ]
        }
    except Exception as error:
        raise HTTPException(503, f"MCP unavailable: {error}") from error

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    if req.stream:
        return StreamingResponse(_event_stream(req), media_type="text/event-stream")

    request_messages = _inject_query_guidance(req.messages)

    payload = {
        "model": req.model or "local",
        "messages": request_messages,
        "temperature": req.temperature if req.temperature is not None else 0.2,
        "tools": TOOLS,
        "tool_choice": req.tool_choice if req.tool_choice is not None else "auto",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        r1 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload)
        r1.raise_for_status()
        data1 = r1.json()

        msg1 = data1["choices"][0]["message"]
        tool_calls = msg1.get("tool_calls")
        if not tool_calls:
            return data1

        tool_messages = []
        section_lookup_result = None
        chord_lookup_result = None
        cursor_lookup_result = None
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_call_id = tc["id"]
            raw_args = tc["function"].get("arguments", "{}")

            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                raise HTTPException(400, f"Tool arguments invalid JSON for {tool_name}: {raw_args}")

            result = await call_mcp(tool_name, args)
            if tool_name == "mcp_find_section":
                section_lookup_result = result
            if tool_name == "mcp_find_chord":
                chord_lookup_result = result
            if tool_name == "mcp_read_cursor":
                cursor_lookup_result = result

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": _render_tool_result(tool_name, result)
            })

        if section_lookup_result is not None and _is_section_timing_question(request_messages):
            payload2 = {**payload, "messages": _build_section_answer_messages(request_messages, section_lookup_result), "tools": [], "tool_choice": "none"}
            r2 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload2)
            r2.raise_for_status()
            return r2.json()

        if chord_lookup_result is not None:
            payload2 = {**payload, "messages": _build_chord_answer_messages(request_messages, chord_lookup_result), "tools": [], "tool_choice": "none"}
            r2 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload2)
            r2.raise_for_status()
            return r2.json()

        if cursor_lookup_result is not None:
            payload2 = {**payload, "messages": _build_cursor_answer_messages(request_messages, cursor_lookup_result), "tools": [], "tool_choice": "none"}
            r2 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload2)
            r2.raise_for_status()
            return r2.json()

        payload2 = {
            **payload,
            "messages": request_messages + [msg1] + tool_messages + [{
                "role": "system",
                "content": (
                    "Answer strictly from the tool outputs already provided in this conversation. "
                    "Do not mention the song name unless the original question explicitly asks for it. "
                    "Do not say that you lack access to databases, metadata, websites, or external tools. "
                    "Use exact values present in the tool outputs, including times, bars, beats, fixture ids, cue effects, and loudness statistics. "
                    "When both bar.beat and seconds are available, present bar.beat first and seconds in parentheses. "
                    "If the requested fact is present in the tool outputs, answer directly with that fact. "
                    "If it is not present, say that the current loaded song data does not contain that fact."
                ),
            }],
        }
        r2 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload2)
        r2.raise_for_status()
        return r2.json()