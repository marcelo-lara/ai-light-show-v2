# LLM Server Module (LLM Guide)

Local inference + tool-gateway stack used for metadata-aware cue planning.

## Submodules

- `models/`: local GGUF model files for llama.cpp.
- `agent-gateway/`: FastAPI service exposing OpenAI-compatible `/v1/chat/completions`.

## Runtime architecture

1. `llm-server` (llama.cpp) serves model inference at `http://llm-server:8080`.
2. Backend `llm.send_prompt` calls `agent-gateway` for tool-using retrieval mode, including recent user and assistant chat turns.
3. `agent-gateway` forwards model requests to llama.cpp and resolves tool calls before the final answer is returned.
4. When the backend requests `stream=true`, `agent-gateway` emits SSE `data:` frames for retrieval-status updates and then relays streamed llama.cpp completion chunks.
5. If model emits tool calls, gateway maps song queries to MCP methods and backend show queries to backend HTTP context routes.
6. Gateway uses persistent SSE MCP session and JSON-RPC over `/messages/?session_id=...`.
7. Tool results are appended as `role=tool` messages before second model pass.

## Backend retrieval path

- Backend-owned prompt profiles live under `backend/api/intents/llm/prompt_profiles/`.
- The backend sends composed `system` messages plus recent user/assistant chat history and the latest user prompt to `agent-gateway`.
- `agent-gateway` can query song metadata tools and backend intent, song, section, cue, and fixture context tools before the final response.
- In streaming mode, retrieval statuses are emitted before each tool call and assistant text is emitted incrementally even when the first model pass answers directly without tool use.
- Conversation history is preserved across turns so the model can interpret follow-up confirmations like `yes, clear it` against the prior destructive request in the same chat.
- The gateway does not synthesize hardcoded answers from retrieval data. Exact timings and other grounded facts must come from model/tool execution; if retrieval or generation fails, the request fails instead of falling back to fabricated output.
- Use this path for cue-sheet review/edit guidance and other song-aware, fixture-aware assistant responses.

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

- `mcp_get_onsets` → `query_feature`
- `backend_get_intent_catalog` → backend `/llm/context/intents`
- `backend_get_current_song_position` → backend `/llm/context/playback`
- `backend_get_song_context` → backend `/llm/context/song`
- `backend_get_song_sections` → backend `/llm/context/sections`
- `backend_get_section_by_name` → backend `/llm/context/sections/by-name/{section_name}`
- `backend_get_section_at_time` → backend `/llm/context/sections/at-time?time_s=...`
- `backend_get_current_cue_sheet` → backend `/llm/context/cues/current`
- `backend_add_cue_row` → backend `/llm/actions/cues/add`
- `backend_update_cue_row_by_index` → backend `/llm/actions/cues/update`
- `backend_delete_cue_row_by_index` → backend `/llm/actions/cues/delete`
- `backend_clear_cue_range` → backend `/llm/actions/cues/clear`
- `backend_apply_cue_helper` → backend `/llm/actions/cues/apply-helper`
- `backend_get_cue_window` → backend `/llm/context/cues/window?start_s=...&end_s=...`
- `backend_get_cue_section` → backend `/llm/context/cues/section/{section_name}`
- `backend_get_fixtures` → backend `/llm/context/fixtures`
- `backend_get_fixture_details` → backend `/llm/context/fixtures/{fixture_id}`

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
5. Do not add hardcoded answer generation or silent fallback paths; unresolved retrieval/model failures must surface as errors.
