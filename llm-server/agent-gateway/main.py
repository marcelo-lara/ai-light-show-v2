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

    if tool_name in {"mcp_read_beats", "mcp_read_chords", "mcp_read_loudness"}:
        song = str(args.get("song") or args.get("song_id") or "")
        payload = {key: value for key, value in args.items() if key in {"start_time", "end_time", "section"}}
        if song:
            payload["song"] = song
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)

    if tool_name == "mcp_read_cue_window":
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], {"start_time": float(args.get("start_time", 0.0)), "end_time": float(args.get("end_time", 0.0))})

    return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], args)


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
                tool_messages.append({"role": "tool", "tool_call_id": tc["id"], "content": orjson.dumps(result).decode("utf-8")})
            if write_proposal is not None:
                yield f"data: {orjson.dumps(write_proposal).decode('utf-8')}\n\n"
                break
            messages = messages + tool_messages

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