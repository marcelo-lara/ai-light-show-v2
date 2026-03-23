import os, json, asyncio, logging, re
import httpx, orjson
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from mcp_client import McpSseConnection

log = logging.getLogger("agent-gateway")
logging.basicConfig(level=logging.INFO)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://llm-server:8080")
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://song-metadata-mcp:8089")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://backend:5001")

# ---- OpenAI-style tools exposed to the model ----
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "backend_get_intent_catalog",
            "description": "Get the catalog of supported backend API intents and their payload keys. Use this before suggesting or planning cue-sheet edits so recommendations stay within supported intent operations.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_get_current_song_position",
            "description": "Get the current song position for the loaded song, including the current section. Treat 'cursor' as the current song position. Use this first for questions like 'where is the cursor?' or 'what section am I at right now?'.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_get_song_context",
            "description": "Get the loaded song details from the backend, including song name, BPM, duration, and song key. Use this for direct song metadata questions.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_get_current_cue_sheet",
            "description": "Get the current cue sheet for the loaded song, including cue row indices. Use this before reviewing or proposing cue-sheet edits.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_add_cue_row",
            "description": "Add one new cue row to the current cue sheet. Use this for requests to add, create, or insert a cue. Never use this to modify, delete, or clear existing cues.",
            "parameters": {
                "type": "object",
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "time": {"type": "number"},
                            "fixture_id": {"type": "string"},
                            "effect": {"type": "string"},
                            "duration": {"type": "number"},
                            "data": {"type": "object"}
                        },
                        "required": ["time", "fixture_id", "effect"]
                    },
                    {
                        "type": "object",
                        "properties": {
                            "time": {"type": "number"},
                            "chaser_id": {"type": "string"},
                            "data": {"type": "object"}
                        },
                        "required": ["time", "chaser_id"]
                    }
                ],
                "properties": {
                    "time": {"type": "number"},
                    "fixture_id": {"type": "string"},
                    "effect": {"type": "string"},
                    "duration": {"type": "number"},
                    "data": {"type": "object"},
                    "chaser_id": {"type": "string"}
                },
                "required": ["time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_update_cue_row_by_index",
            "description": "Update one existing cue row by index. Use this only to modify a known existing row from the current cue sheet. Never use this to add a new cue or clear a range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "patch": {"type": "object"}
                },
                "required": ["index", "patch"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_delete_cue_row_by_index",
            "description": "Delete one existing cue row by index. This is destructive. Use it only after the user explicitly confirms the deletion in a later turn. Never use this to clear a range or add a cue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"}
                },
                "required": ["index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_clear_cue_range",
            "description": "Clear cue rows in a time range. This is destructive. Use it only after the user explicitly confirms the clear in a later turn, after you summarize the affected range or section. Never use this to add or modify one cue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_time": {"type": "number"},
                    "to_time": {"type": "number"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_apply_cue_helper",
            "description": "Apply a supported cue helper to generate cue rows. Use this only when the user explicitly asks for helper-based cue generation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "helper_id": {"type": "string"}
                },
                "required": ["helper_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_get_song_sections",
            "description": "Get the normalized section list for the loaded song, including section names with start and end timestamps. Use this for general section overview questions.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_get_section_by_name",
            "description": "Get the start and end timestamps for one named section in the loaded song. Use only for direct timing questions such as 'where does the verse start?' or 'intro?'. Do not use this for fixture-in-section or effect-in-section questions.",
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
            "name": "backend_get_section_at_time",
            "description": "Get the section that contains a specific song time or cursor position. Example: 'what section is at the cursor (60.000)?'. Do not use onset tools for cursor-position section lookup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_s": {"type": "number"}
                },
                "required": ["time_s"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_get_cue_window",
            "description": "Get cue-sheet activity for a time window, including raw cues, expanded effect cues, fixtures used, and effects used. Example: 'what effects will be rendered in the first 30 seconds?'. Do not use onset tools for cue-window questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_s": {"type": "number"},
                    "end_s": {"type": "number"}
                },
                "required": ["start_s", "end_s"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_get_cue_section",
            "description": "Get cue-sheet activity for one named section, including that section's fixtures and effects. Example: 'what fixtures are used in the verse?'. Do not use onset tools for section fixture/effect questions.",
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
            "name": "backend_get_fixtures",
            "description": "Get the configured fixtures available in the current show, including fixture ids, names, types, and supported effects.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backend_get_fixture_details",
            "description": "Get detailed information for one configured fixture, including meta channels, mappings, and supported effects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fixture_id": {"type": "string"}
                },
                "required": ["fixture_id"]
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

# ---- Persistent MCP connection ----
mcp = McpSseConnection(MCP_BASE_URL)

async def ensure_mcp_started():
    # keep retrying in case MCP is still starting
    for attempt in range(1, 61):
        try:
            await mcp.start()
            log.info("MCP connected.")
            return
        except Exception as e:
            log.warning("MCP not ready (attempt %s): %s", attempt, e)
            await asyncio.sleep(1)
    log.error("MCP did not become ready in time.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(ensure_mcp_started())
    yield
    task.cancel()
    await mcp.close()

app = FastAPI(lifespan=lifespan)

# ---- MCP tool wrapper ----
MCP_TOOL_MAP = {
    "mcp_get_onsets": "query_feature",
}

BACKEND_STATUS_MAP = {
    "backend_get_intent_catalog": "Loading supported intents",
    "backend_get_current_song_position": "Looking up current song position",
    "backend_get_song_context": "Looking up song details",
    "backend_get_current_cue_sheet": "Reviewing current cue sheet",
    "backend_add_cue_row": "Adding cue row",
    "backend_update_cue_row_by_index": "Updating cue row",
    "backend_delete_cue_row_by_index": "Deleting cue row",
    "backend_clear_cue_range": "Clearing cue rows",
    "backend_apply_cue_helper": "Applying cue helper",
    "backend_get_song_sections": "Looking up song sections",
    "backend_get_section_by_name": "Looking up section timing",
    "backend_get_section_at_time": "Looking up cursor section",
    "backend_get_cue_window": "Looking up cue window",
    "backend_get_cue_section": "Looking up section cues",
    "backend_get_fixtures": "Looking up available fixtures",
    "backend_get_fixture_details": "Checking fixture capabilities",
}


def normalize_mcp_tool_call(tool_name: str, args: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    real_tool = MCP_TOOL_MAP[tool_name]

    if tool_name == "mcp_get_onsets":
        song = args.get("song") or args.get("song_id")
        if not song:
            raise HTTPException(400, "mcp_get_onsets requires 'song' or 'song_id'")

        feature = args.get("feature", "analyzer.beats")
        normalized = {
            "song": song,
            "feature": feature,
            "mode": args.get("mode", "summary"),
            "include_raw": args.get("include_raw", False),
        }

        if "start_time" in args:
            normalized["start_time"] = args["start_time"]
        if "end_time" in args:
            normalized["end_time"] = args["end_time"]
        if "max_points" in args:
            normalized["max_points"] = args["max_points"]
        if "time_tolerance_ms" in args:
            normalized["time_tolerance_ms"] = args["time_tolerance_ms"]

        return real_tool, normalized

    return real_tool, args

async def call_mcp(tool_name: str, args: Dict[str, Any]) -> Any:
    if tool_name not in MCP_TOOL_MAP:
        # return a structured error so the LLM can react
        return {
            "error": "MCP_TOOL_NOT_MAPPED",
            "tool_name": tool_name,
            "available_mappings": list(MCP_TOOL_MAP.keys()),
            "hint": "Call /debug/mcp/tools and map MCP_TOOL_MAP to real tool names."
        }

    real_tool, normalized_args = normalize_mcp_tool_call(tool_name, args)
    # MCP JSON-RPC tools/call
    req = {
        "jsonrpc": "2.0",
        "id": int(asyncio.get_event_loop().time() * 1000) % 1000000000,
        "method": "tools/call",
        "params": {"name": real_tool, "arguments": normalized_args}
    }
    try:
        resp = await mcp.request(req, timeout=15)
        return resp
    except Exception as e:
        return {"error": "MCP_CALL_FAILED", "detail": str(e), "tool": tool_name, "args": normalized_args}


async def call_backend(tool_name: str, args: Dict[str, Any]) -> Any:
    if tool_name == "backend_get_intent_catalog":
        method = "GET"
        path = "/llm/context/intents"
        params = None
        json_body = None
    elif tool_name == "backend_get_current_song_position":
        method = "GET"
        path = "/llm/context/playback"
        params = None
        json_body = None
    elif tool_name == "backend_get_song_context":
        method = "GET"
        path = "/llm/context/song"
        params = None
        json_body = None
    elif tool_name == "backend_get_current_cue_sheet":
        method = "GET"
        path = "/llm/context/cues/current"
        params = None
        json_body = None
    elif tool_name == "backend_add_cue_row":
        method = "POST"
        path = "/llm/actions/cues/add"
        params = None
        json_body = {"payload": args}
    elif tool_name == "backend_update_cue_row_by_index":
        method = "POST"
        path = "/llm/actions/cues/update"
        params = None
        json_body = {"payload": args}
    elif tool_name == "backend_delete_cue_row_by_index":
        method = "POST"
        path = "/llm/actions/cues/delete"
        params = None
        json_body = {"payload": args}
    elif tool_name == "backend_clear_cue_range":
        method = "POST"
        path = "/llm/actions/cues/clear"
        params = None
        json_body = {"payload": args}
    elif tool_name == "backend_apply_cue_helper":
        method = "POST"
        path = "/llm/actions/cues/apply-helper"
        params = None
        json_body = {"payload": args}
    elif tool_name == "backend_get_song_sections":
        method = "GET"
        path = "/llm/context/sections"
        params = None
        json_body = None
    elif tool_name == "backend_get_section_by_name":
        section_name = args.get("section_name")
        if not section_name:
            return {"error": "BACKEND_TOOL_INVALID_ARGS", "tool": tool_name, "detail": "section_name is required"}
        method = "GET"
        path = f"/llm/context/sections/by-name/{section_name}"
        params = None
        json_body = None
    elif tool_name == "backend_get_section_at_time":
        time_s = args.get("time_s")
        if time_s is None:
            return {"error": "BACKEND_TOOL_INVALID_ARGS", "tool": tool_name, "detail": "time_s is required"}
        method = "GET"
        path = "/llm/context/sections/at-time"
        params = {"time_s": time_s}
        json_body = None
    elif tool_name == "backend_get_cue_window":
        start_s = args.get("start_s")
        end_s = args.get("end_s")
        if start_s is None or end_s is None:
            return {"error": "BACKEND_TOOL_INVALID_ARGS", "tool": tool_name, "detail": "start_s and end_s are required"}
        method = "GET"
        path = "/llm/context/cues/window"
        params = {"start_s": start_s, "end_s": end_s}
        json_body = None
    elif tool_name == "backend_get_cue_section":
        section_name = args.get("section_name")
        if not section_name:
            return {"error": "BACKEND_TOOL_INVALID_ARGS", "tool": tool_name, "detail": "section_name is required"}
        method = "GET"
        path = f"/llm/context/cues/section/{section_name}"
        params = None
        json_body = None
    elif tool_name == "backend_get_fixtures":
        method = "GET"
        path = "/llm/context/fixtures"
        params = None
        json_body = None
    elif tool_name == "backend_get_fixture_details":
        fixture_id = args.get("fixture_id")
        if not fixture_id:
            return {"error": "BACKEND_TOOL_INVALID_ARGS", "tool": tool_name, "detail": "fixture_id is required"}
        method = "GET"
        path = f"/llm/context/fixtures/{fixture_id}"
        params = None
        json_body = None
    else:
        return {"error": "BACKEND_TOOL_NOT_MAPPED", "tool": tool_name}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            if method == "POST":
                response = await client.post(f"{BACKEND_BASE_URL}{path}", json=json_body)
            else:
                response = await client.get(f"{BACKEND_BASE_URL}{path}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as error:
            return {"error": "BACKEND_CALL_FAILED", "tool": tool_name, "detail": str(error)}


def sse_data(payload: Any) -> bytes:
    encoded = payload if isinstance(payload, bytes) else orjson.dumps(payload)
    return b"data: " + encoded + b"\n\n"


def sse_done() -> bytes:
    return b"data: [DONE]\n\n"


def split_stream_content(content: str, max_chunk_size: int = 24) -> List[str]:
    if not content:
        return []

    chunks: List[str] = []
    current = ""
    for part in re.findall(r"\S+\s*|\s+", content):
        remaining = part
        while remaining:
            available = max_chunk_size - len(current)
            if available <= 0:
                chunks.append(current)
                current = ""
                available = max_chunk_size

            if len(remaining) <= available:
                current += remaining
                remaining = ""
                continue

            current += remaining[:available]
            remaining = remaining[available:]

    if current:
        chunks.append(current)
    return chunks


def build_payload(req: ChatRequest) -> Dict[str, Any]:
    return {
        "model": req.model or "local",
        "messages": req.messages,
        "temperature": req.temperature if req.temperature is not None else 0.2,
        "tools": TOOLS,
        "tool_choice": req.tool_choice if req.tool_choice is not None else "auto",
    }


def latest_user_message(messages: List[Dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            return content if isinstance(content, str) else ""
    return ""


def is_destructive_backend_tool(tool_name: str) -> bool:
    return tool_name in {"backend_delete_cue_row_by_index", "backend_clear_cue_range"}


def has_explicit_confirmation(user_message: str) -> bool:
    normalized = str(user_message or "").strip().lower()
    if not normalized:
        return False
    return bool(re.search(r"\b(yes|confirm|confirmed|go ahead|proceed|do it|please do|clear it|delete it)\b", normalized))


def confirmation_required_result(tool_name: str) -> Dict[str, Any]:
    if tool_name == "backend_clear_cue_range":
        answer = "This will remove existing cue rows. Do you want me to clear that range? Reply 'yes, clear it' to confirm."
    else:
        answer = "This will remove an existing cue row. Do you want me to delete it? Reply 'yes, delete it' to confirm."
    return {
        "error": "BACKEND_CONFIRMATION_REQUIRED",
        "tool": tool_name,
        "detail": "Explicit user confirmation is required before destructive cue deletes or clears.",
        "required_confirmation": "Ask for confirmation and wait for a later user reply such as 'yes, clear it' or 'confirm delete'.",
        "answer": answer,
    }


async def resolve_tool_call(tool_name: str, args: Dict[str, Any], user_message: str = "") -> Any:
    if is_destructive_backend_tool(tool_name) and not has_explicit_confirmation(user_message):
        return confirmation_required_result(tool_name)
    if tool_name in MCP_TOOL_MAP:
        return await call_mcp(tool_name, args)
    return await call_backend(tool_name, args)


async def stream_llama_completion(payload: Dict[str, Any]) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{LLM_BASE_URL}/v1/chat/completions", json={**payload, "stream": True}) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                stripped = line.strip()
                if stripped.startswith("data:"):
                    yield f"{stripped}\n\n".encode("utf-8")


async def stream_chat_completion(req: ChatRequest) -> AsyncIterator[bytes]:
    payload = build_payload(req)
    user_message = latest_user_message(req.messages)

    yield sse_data({"type": "status", "status": "Looking up song and fixture details"})

    async with httpx.AsyncClient(timeout=120.0) as client:
        first_response = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload)
        first_response.raise_for_status()
        first_data = first_response.json()

    message = first_data["choices"][0]["message"]
    tool_calls = message.get("tool_calls")
    if not tool_calls:
        content = message.get("content")
        if isinstance(content, str) and content:
            for chunk in split_stream_content(content):
                yield sse_data({"choices": [{"delta": {"content": chunk}, "finish_reason": None}]})
            yield sse_done()
            return
        yield sse_data({"type": "error", "error": "llm_empty_response"})
        yield sse_done()
        return

    tool_messages = []
    for tc in tool_calls:
        tool_name = tc["function"]["name"]
        tool_call_id = tc["id"]
        raw_args = tc["function"].get("arguments", "{}")

        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            yield sse_data({"type": "error", "error": f"invalid_tool_args:{tool_name}"})
            yield sse_done()
            return

        status = BACKEND_STATUS_MAP.get(tool_name)
        if status and not (is_destructive_backend_tool(tool_name) and not has_explicit_confirmation(user_message)):
            yield sse_data({"type": "status", "status": status})

        result = await resolve_tool_call(tool_name, args, user_message)
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": orjson.dumps(result).decode("utf-8")
        })

    followup_payload = {**payload, "messages": req.messages + [message] + tool_messages, "tool_choice": "none"}
    try:
        async for chunk in stream_llama_completion(followup_payload):
            yield chunk
    except Exception as error:
        yield sse_data({"type": "error", "error": str(error) or "llm_stream_failed"})
        yield sse_done()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/debug/mcp/tools")
async def debug_mcp_tools():
    # List MCP tools so you can fill MCP_TOOL_MAP
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    try:
        return await mcp.request(req, timeout=10)
    except Exception as error:
        raise HTTPException(503, f"MCP unavailable: {error}") from error

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    payload = build_payload(req)
    user_message = latest_user_message(req.messages)

    if req.stream:
        return StreamingResponse(stream_chat_completion(req), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=120.0) as client:
        r1 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload)
        r1.raise_for_status()
        data1 = r1.json()

        msg1 = data1["choices"][0]["message"]
        tool_calls = msg1.get("tool_calls")
        if not tool_calls:
            return data1

        tool_messages = []
        statuses = []
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_call_id = tc["id"]
            raw_args = tc["function"].get("arguments", "{}")

            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                raise HTTPException(400, f"Tool arguments invalid JSON for {tool_name}: {raw_args}")

            status = BACKEND_STATUS_MAP.get(tool_name)
            if status and not (is_destructive_backend_tool(tool_name) and not has_explicit_confirmation(user_message)):
                statuses.append(status)

            result = await resolve_tool_call(tool_name, args, user_message)

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": orjson.dumps(result).decode("utf-8")
            })

        payload2 = {**payload, "messages": req.messages + [msg1] + tool_messages, "tool_choice": "none"}
        r2 = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload2)
        r2.raise_for_status()
        data2 = r2.json()
        data2["agent_statuses"] = statuses
        return data2