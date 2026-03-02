# Agent Gateway (LLM Guide)

FastAPI OpenAI-compatible wrapper for local llama.cpp with MCP tool-calling support.

## API surface

- `POST /v1/chat/completions`: OpenAI-style completion endpoint.
- `GET /health`: liveness.
- `GET /debug/mcp/tools`: MCP tools discovery via JSON-RPC `tools/list`.

## Core flow

1. Forward user chat request to llama.cpp.
2. If no tool calls, return model output directly.
3. If tool calls exist:
   - normalize arguments,
   - map LLM tool name to MCP tool name,
   - execute MCP `tools/call` via persistent SSE session,
   - append tool results as `role=tool` messages,
   - call model again and return final output.

## MCP transport behavior

Implemented in `mcp_client.py`:

- Open `/sse` and parse `event: endpoint`.
- Keep stream open for the same session.
- Auto-initialize MCP session (`initialize` + `notifications/initialized`).
- POST JSON-RPC to `/messages/?session_id=...`.
- Resolve responses by JSON-RPC `id` from SSE `data:` events.

## Environment variables

- `LLM_BASE_URL` (default: `http://llm-server:8080`)
- `MCP_BASE_URL` (default: `http://song-metadata-mcp:8089`)

## Current tool mapping

- `mcp_get_sections` → `get_song_overview`
- `mcp_get_onsets` → `query_feature`

## LLM contributor checklist

1. Keep mappings explicit and easy to audit.
2. Fail with structured errors when mapping/args are invalid.
3. Preserve persistent-session MCP semantics.
4. Avoid startup hard-fail loops; keep retry behavior bounded.
