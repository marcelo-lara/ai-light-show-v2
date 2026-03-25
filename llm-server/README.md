# LLM Server Module (LLM Guide)

Local inference + tool-gateway stack used for metadata-aware cue planning.

## Submodules

- `models/`: local GGUF model files for llama.cpp.
- `agent-gateway/`: FastAPI service exposing OpenAI-compatible `/v1/chat/completions`.

## Runtime architecture

1. `llm-server` (llama.cpp) serves model inference at `http://llm-server:8080`.
2. `agent-gateway` accepts chat requests and forwards to llama.cpp.
3. If model emits tool calls, gateway maps tools to MCP methods.
4. Gateway connects to the backend-mounted MCP endpoint at `/mcp` over Streamable HTTP.
5. Tool results are appended as `role=tool` messages before second model pass.

## Key files

- `agent-gateway/main.py`: API surface, tool definitions, tool-call loop.
- `agent-gateway/requirements.txt`

## MCP integration constraints

- Use the backend-mounted MCP endpoint instead of a standalone metadata service.
- Use Streamable HTTP for new deployments.
- Keep tool-call argument normalization explicit in the gateway.

## Tool mapping (current)

- `mcp_get_sections` → `metadata_get_sections`
- `mcp_get_onsets` → `metadata_get_beats`

## Development

Run through Docker Compose for consistent networking:

```bash
docker compose up llm-server agent-gateway backend --build
```

Host endpoints:

- llama.cpp: `http://localhost:8080`
- gateway: `http://localhost:8090`
- gateway debug MCP tools: `GET /debug/mcp/tools`

## LLM contributor checklist

1. Do not create duplicate FastAPI app instances.
2. Do not use container suffix hostnames; use compose service names.
3. Keep tool-call argument normalization explicit and deterministic.
4. Keep the gateway aligned with the backend-mounted MCP HTTP surface and update mappings when MCP tool names change.
