import json
import logging
import os
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
            "description": "Read the song sections with exact names and time ranges.",
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
    "mcp_read_chords": "metadata_get_chords",
    "mcp_read_cue_window": "cues_get_window",
    "mcp_read_fixtures": "fixtures_list",
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


async def _call_mcp_tool(name: str, arguments: Dict[str, Any]) -> Any:
    async with Client(MCP_BASE_URL) as client:
        result = await client.call_tool(name, arguments, raise_on_error=False)
    if result.is_error:
        detail = None
        if result.content and hasattr(result.content[0], "text"):
            detail = result.content[0].text
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

    if tool_name in {"mcp_read_beats", "mcp_read_chords", "mcp_read_loudness"}:
        song = str(args.get("song") or args.get("song_id") or "")
        payload = {key: value for key, value in args.items() if key in {"start_time", "end_time", "section"}}
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
        lines.append(f"- {name}: start={start_time:.3f}s end={end_time:.3f}s")
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


def _format_chords(result: Dict[str, Any]) -> str:
    payload = ((result.get("data") or {}) if result.get("ok") else {}) if isinstance(result, dict) else {}
    chords = payload.get("chords") or []
    song = payload.get("song") or "unknown"
    if not chords:
        return f"Song: {song}\nChords: unavailable"
    lines = [f"Song: {song}", "Chords:"]
    for chord in chords[:32]:
        lines.append(f"- time={float(chord.get('time_s', 0.0)):.3f}s chord={chord.get('chord', 'unknown')}")
    return "\n".join(lines)


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
    if tool_name == "mcp_read_chords":
        return _format_chords(result)
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
            f"song={payload.get('song', 'unknown')}\n"
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
                "If section_found=true, never say the data is missing. "
                "Answer the original question directly with the exact numeric time and 's' suffix. "
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


def _proposal_for_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
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
    payload = {
        "model": req.model or "local",
        "messages": req.messages,
        "temperature": req.temperature if req.temperature is not None else 0.2,
        "tools": TOOLS,
        "tool_choice": req.tool_choice if req.tool_choice is not None else "auto",
    }

    async with httpx.AsyncClient(timeout=240.0) as client:
        yield f"data: {orjson.dumps({'type': 'status', 'phase': 'thinking', 'label': 'Thinking'}).decode('utf-8')}\n\n"
        messages = list(req.messages)
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
                tool_messages.append({"role": "tool", "tool_call_id": tc["id"], "content": _render_tool_result(tool_name, result)})
            if write_proposal is not None:
                yield f"data: {orjson.dumps(write_proposal).decode('utf-8')}\n\n"
                break
            if section_lookup_result is not None:
                messages = _build_section_answer_messages(messages, section_lookup_result)
                continue
            messages = messages + tool_messages + [{
                "role": "system",
                "content": (
                    "Answer strictly from the tool outputs already provided in this conversation. "
                    "Do not say that you lack access to databases, metadata, websites, or external tools. "
                    "If a tool output contains SECTION_LOOKUP_RESULT with section_found=true, you must answer with the exact "
                    "section_start_seconds or section_end_seconds value from that tool output. "
                    "Do not ask for more context when that exact section value is already present. "
                    "If the requested section name appears in the tool outputs, report its exact start or end time directly. "
                    "If it does not appear, say that the current loaded song data does not contain that section name."
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

    payload = {
        "model": req.model or "local",
        "messages": req.messages,
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

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": _render_tool_result(tool_name, result)
            })

        if section_lookup_result is not None:
            payload2 = {**payload, "messages": _build_section_answer_messages(req.messages, section_lookup_result), "tools": [], "tool_choice": "none"}
            r2 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload2)
            r2.raise_for_status()
            return r2.json()

        payload2 = {
            **payload,
            "messages": req.messages + [msg1] + tool_messages + [{
                "role": "system",
                "content": (
                    "Answer strictly from the tool outputs already provided in this conversation. "
                    "Do not say that you lack access to databases, metadata, websites, or external tools. "
                    "If a tool output contains SECTION_LOOKUP_RESULT with section_found=true, you must answer with the exact "
                    "section_start_seconds or section_end_seconds value from that tool output. "
                    "Do not ask for more context when that exact section value is already present. "
                    "If the requested section name appears in the tool outputs, report its exact start or end time directly. "
                    "If it does not appear, say that the current loaded song data does not contain that section name."
                ),
            }],
        }
        r2 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload2)
        r2.raise_for_status()
        return r2.json()