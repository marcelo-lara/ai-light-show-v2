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

## Fast-path assistant behavior

The gateway also performs deterministic fast-path handling for common assistant requests before relying on a follow-up model turn.

- Whole-sheet cue clear phrases resolve to a dedicated clear-all proposal instead of a synthetic `0..0` time window.
- Chord-conditioned edit prompts for prisms, parcans, and protons resolve to grounded cue-add proposals using backend metadata and fixture lists.
- `none` chord spans are resolved from analyzer label `N` and can produce `blackout` or `fade_out` cue proposals across the full span.
- Write-capable turns stop at proposal generation so backend can require explicit confirmation before mutating cues.

## Response shaping

- Grounded timing answers prefer `bar.beat (seconds)` when tool results provide both values.
- The default assistant prompt avoids repeating the loaded song name unless the user explicitly asks for it.
- Proposal summaries preserve effect names where the distinction matters, including `blackout` and `fade_out`.

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

The gateway also uses backend-mounted tools for transport cursor lookup, section/beat/chord/loudness grounding, fixture discovery, chaser discovery, and cue-sheet reads used to shape assistant proposals and summaries.

## LLM contributor checklist

1. Keep mappings explicit and easy to audit.
2. Fail with structured errors when mapping/args are invalid.
3. Keep the backend MCP URL pointed at the mounted backend endpoint.
4. Preserve deterministic tool result shapes back to the LLM.
