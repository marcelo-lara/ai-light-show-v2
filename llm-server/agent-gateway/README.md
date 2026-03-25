# Agent Gateway (LLM Guide)

FastAPI OpenAI-compatible wrapper for local llama.cpp with MCP tool-calling support.

## API surface

- `POST /v1/chat/completions`: OpenAI-style completion endpoint.
- `GET /health`: liveness.
- `GET /debug/mcp/tools`: MCP tools discovery via FastMCP HTTP client.

## Core flow

1. Forward user chat request to llama.cpp.
2. If no tool calls, return model output directly.
3. If tool calls exist:
   - normalize arguments,
   - map LLM tool name to MCP tool name,
   - execute MCP tool calls via Streamable HTTP,
   - append tool results as `role=tool` messages,
   - call model again and return final output.

## MCP transport behavior

Implemented directly in `main.py` via `fastmcp.Client` against a Streamable HTTP MCP endpoint.

- Connect to backend MCP URL with automatic initialization.
- Call tools through the typed client API.
- Keep gateway transport stateless and simple.

## Environment variables

- `LLM_BASE_URL` (default: `http://llm-server:8080`)
- `MCP_BASE_URL` (default: `http://backend:5001/mcp`)

## Current tool mapping

- `mcp_get_sections` → `metadata_get_sections`
- `mcp_get_onsets` → `metadata_get_beats` with optional section windowing and subdivision expansion in the gateway

## LLM contributor checklist

1. Keep mappings explicit and easy to audit.
2. Fail with structured errors when mapping/args are invalid.
3. Keep the backend MCP URL pointed at the mounted backend endpoint.
4. Preserve deterministic tool result shapes back to the LLM.
