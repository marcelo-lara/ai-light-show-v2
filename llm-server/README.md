# LLM Server Module (LLM Guide)

Local inference + tool-gateway stack used for metadata-aware cue planning.

## Submodules

- `models/`: local GGUF model files for llama.cpp.
- `agent-gateway/`: FastAPI service exposing OpenAI-compatible `/v1/chat/completions`.

## Runtime architecture

1. `llm-server` (llama.cpp) serves model inference at `http://llm-server:8080`.
2. `agent-gateway` accepts chat requests and forwards to llama.cpp.
3. If model emits tool calls, gateway maps tools to MCP methods.
4. Gateway uses persistent SSE MCP session and JSON-RPC over `/messages/?session_id=...`.
5. Tool results are appended as `role=tool` messages before second model pass.

## Key files

- `agent-gateway/main.py`: API surface, tool definitions, tool-call loop.
- `agent-gateway/mcp_client.py`: persistent SSE MCP transport + initialization handshake.
- `agent-gateway/requirements.txt`

## MCP integration constraints

- Keep one SSE stream open per MCP session.
- Parse `event: endpoint` to get session-bound messages URL.
- Initialize MCP session before tool methods (`initialize` + `notifications/initialized`).
- Post JSON-RPC to session messages endpoint and read response via the same SSE stream.

## Tool mapping (current)

- `mcp_get_sections` → `get_song_overview`
- `mcp_get_onsets` → `query_feature`

## Development

Run through Docker Compose for consistent networking:

```bash
docker compose up llm-server agent-gateway song-metadata-mcp --build
```

Host endpoints:

- llama.cpp: `http://localhost:8080`
- gateway: `http://localhost:8090`
- gateway debug MCP tools: `GET /debug/mcp/tools`

## LLM contributor checklist

1. Do not create duplicate FastAPI app instances.
2. Do not use container suffix hostnames; use compose service names.
3. Keep tool-call argument normalization explicit and deterministic.
4. Any MCP transport changes must preserve persistent-session semantics.
