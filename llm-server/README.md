# LLM Server Module (LLM Guide)

Local inference + tool-gateway stack used for metadata-aware cue planning.

## Submodules

- `models/`: local GGUF model files for llama.cpp.
- `agent-gateway/`: FastAPI service exposing OpenAI-compatible `/v1/chat/completions`.

## Runtime architecture

1. `llm-server` (llama.cpp) serves model inference at `http://llm-server:8080`.
2. `agent-gateway` accepts chat requests and forwards to llama.cpp.
3. If model emits read tool calls, gateway maps them to backend MCP methods and loops until the model produces a final answer.
4. If model emits write proposal tools, gateway stops before mutation and streams a structured proposal event back to the backend assistant service.
5. Gateway connects to the backend-mounted MCP endpoint at `/mcp` over Streamable HTTP.
6. Backend confirmation applies the proposed action and then requests a model-authored follow-up response.

## Key files

- `agent-gateway/main.py`: API surface, tool definitions, tool-call loop.
- `agent-gateway/requirements.txt`

## MCP integration constraints

- Use the backend-mounted MCP endpoint instead of a standalone metadata service.
- Use Streamable HTTP for new deployments.
- Keep tool-call argument normalization explicit in the gateway.

## Tool mapping (current)

- `mcp_read_sections` → `metadata_get_sections`
- `mcp_read_beats` → `metadata_get_beats`
- `mcp_read_chords` → `metadata_get_chords`
- `mcp_read_cue_window` → `cues_get_window`
- `mcp_read_fixtures` → `fixtures_list`
- `mcp_read_chasers` → `chasers_list`
- `mcp_read_cursor` → `transport_get_cursor`
- `mcp_read_loudness` → `metadata_get_loudness`

Write proposal tools handled by the gateway without direct mutation:

- `propose_cue_clear_range`
- `propose_chaser_apply`

## Development

Run through Docker Compose for consistent networking:

```bash
docker compose up llm-server agent-gateway backend --build
```

Host endpoints:

- llama.cpp: `http://localhost:8080`
- gateway: `http://localhost:8090`
- gateway debug MCP tools: `GET /debug/mcp/tools`
- gateway streamed chat: `POST /v1/chat/completions` with `stream=true` returns server-sent JSON events (`status`, `delta`, `done`, `proposal`, `error`)

## LLM contributor checklist

1. Do not create duplicate FastAPI app instances.
2. Do not use container suffix hostnames; use compose service names.
3. Keep tool-call argument normalization explicit and deterministic.
4. Keep the gateway aligned with the backend-mounted MCP HTTP surface and update mappings when MCP tool names change.
