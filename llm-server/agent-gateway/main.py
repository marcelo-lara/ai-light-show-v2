import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
import orjson
from fastmcp import Client
from fastapi import FastAPI, HTTPException
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
            "name": "mcp_get_onsets",
            "description": "Get beat-aligned onset timestamps (or beat positions) for a song section and subdivision.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "string"},
                    "section": {"type": "string"},
                    "subdivision": {"type": "number", "description": "1=beats, 0.5=8ths, 0.25=16ths"}
                },
                "required": ["song_id", "section", "subdivision"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_get_sections",
            "description": "Get list of song sections with start/end (beats or seconds).",
            "parameters": {
                "type": "object",
                "properties": {"song_id": {"type": "string"}},
                "required": ["song_id"]
            }
        }
    },
]

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    model: Optional[str] = "local"
    temperature: Optional[float] = 0.2
    tool_choice: Optional[Any] = "auto"

app = FastAPI()

# ---- MCP tool wrapper ----
MCP_TOOL_MAP = {
    "mcp_get_onsets": "metadata_get_beats",
    "mcp_get_sections": "metadata_get_sections",
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

    if tool_name == "mcp_get_sections":
        song = _require_song_arg(tool_name, args)
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], {"song": song})

    if tool_name == "mcp_get_onsets":
        song = _require_song_arg(tool_name, args)
        section_name = str(args.get("section") or "").strip()
        subdivision = float(args.get("subdivision", 1.0) or 1.0)
        beat_args: Dict[str, Any] = {"song": song}

        if "start_time" in args:
            beat_args["start_time"] = args["start_time"]
        if "end_time" in args:
            beat_args["end_time"] = args["end_time"]

        if section_name and "start_time" not in beat_args and "end_time" not in beat_args:
            sections_result = await _call_mcp_tool("metadata_get_sections", {"song": song})
            if not isinstance(sections_result, dict) or not sections_result.get("ok"):
                return sections_result
            sections = sections_result.get("data", {}).get("sections", [])
            match = next(
                (section for section in sections if str(section.get("name") or "").lower() == section_name.lower()),
                None,
            )
            if match is None:
                return {
                    "ok": False,
                    "error": {
                        "code": "section_not_found",
                        "message": f"Section '{section_name}' not found",
                        "details": {"song": song},
                    },
                }
            beat_args["start_time"] = match.get("start_s")
            beat_args["end_time"] = match.get("end_s")

        beats_result = await _call_mcp_tool(MCP_TOOL_MAP[tool_name], beat_args)
        if not isinstance(beats_result, dict) or not beats_result.get("ok"):
            return beats_result

        beats = beats_result.get("data", {}).get("beats", [])
        beat_times = [float(beat.get("time", 0.0)) for beat in beats if isinstance(beat, dict)]
        return {
            "ok": True,
            "data": {
                "song": song,
                "section": section_name or None,
                "subdivision": subdivision,
                "onsets": _expand_subdivision_times(beat_times, subdivision),
                "beat_count": len(beat_times),
            },
        }

    return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], args)

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
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_call_id = tc["id"]
            raw_args = tc["function"].get("arguments", "{}")

            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                raise HTTPException(400, f"Tool arguments invalid JSON for {tool_name}: {raw_args}")

            result = await call_mcp(tool_name, args)

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": orjson.dumps(result).decode("utf-8")
            })

        payload2 = {**payload, "messages": req.messages + [msg1] + tool_messages}
        r2 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload2)
        r2.raise_for_status()
        return r2.json()