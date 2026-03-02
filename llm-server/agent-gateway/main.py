import os, json, asyncio, logging
import httpx, orjson
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from mcp_sse_client import McpSseConnection  # persistent SSE client you added

log = logging.getLogger("agent-gateway")
logging.basicConfig(level=logging.INFO)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://llm-server:8080")
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://song-metadata-mcp:8089")

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
# IMPORTANT: You MUST map these to the real MCP tool names after you inspect tools/list.
MCP_TOOL_MAP = {
    # "mcp_get_onsets": "YOUR_REAL_MCP_TOOL_NAME_FOR_ONSETS",
    # "mcp_get_sections": "YOUR_REAL_MCP_TOOL_NAME_FOR_SECTIONS",
}

async def call_mcp(tool_name: str, args: Dict[str, Any]) -> Any:
    if tool_name not in MCP_TOOL_MAP:
        # return a structured error so the LLM can react
        return {
            "error": "MCP_TOOL_NOT_MAPPED",
            "tool_name": tool_name,
            "available_mappings": list(MCP_TOOL_MAP.keys()),
            "hint": "Call /debug/mcp/tools and map MCP_TOOL_MAP to real tool names."
        }

    real_tool = MCP_TOOL_MAP[tool_name]
    # MCP JSON-RPC tools/call
    req = {
        "jsonrpc": "2.0",
        "id": int(asyncio.get_event_loop().time() * 1000) % 1000000000,
        "method": "tools/call",
        "params": {"name": real_tool, "arguments": args}
    }
    try:
        resp = await mcp.request(req, timeout=15)
        return resp
    except Exception as e:
        return {"error": "MCP_CALL_FAILED", "detail": str(e), "tool": tool_name, "args": args}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/debug/mcp/tools")
async def debug_mcp_tools():
    # List MCP tools so you can fill MCP_TOOL_MAP
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    return await mcp.request(req, timeout=10)

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