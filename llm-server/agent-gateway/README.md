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
   - execute MCP or backend retrieval/mutation calls,
   - continue through bounded follow-up tool rounds when the model needs more context,
   - if a tool result includes an authoritative `answer` field for a non-edit request, return that answer directly,
   - otherwise append tool results as `role=tool` messages and continue until the model produces a final answer.

The gateway relies on the backend-provided chat history already present in `messages`, so later user replies like `yes` or `no` can be interpreted in the same conversation when deciding whether destructive cue edits are confirmed.
The gateway also honors optional `allowed_tools` from the backend request payload so narrow question classes can restrict the available retrieval tool set without synthesizing an answer.

## Failure policy

- Do not add hardcoded answer generation based on pattern-matching user prompts.
- Do not hide retrieval or model failures behind synthesized fallback text.
- If required retrieval data is unavailable or the model/tool path fails, return a structured error or an empty upstream result that the caller can surface.

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

- `mcp_get_onsets` → `query_feature`
- `backend_get_intent_catalog` → backend `/llm/context/intents`
- `backend_get_current_song_position` → backend `/llm/context/playback`
- `backend_get_song_context` → backend `/llm/context/song`
- `backend_get_song_sections` → backend `/llm/context/sections`
- `backend_get_section_by_name` → backend `/llm/context/sections/by-name/{section_name}`
- `backend_get_section_at_time` → backend `/llm/context/sections/at-time?time_s=...`
- `backend_get_section_beat` → backend `/llm/context/sections/beat?section_name=...&beat_ordinal=...&occurrence=...`
- `backend_get_chord_transition` → backend `/llm/context/chords/transition?from_chord=...&to_chord=...&occurrence=...`
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

## LLM contributor checklist

1. Keep mappings explicit and easy to audit.
2. Fail with structured errors when mapping/args are invalid.
3. Preserve persistent-session MCP semantics.
4. Avoid startup hard-fail loops; keep retry behavior bounded.
5. Do not introduce hardcoded logic or fallback answers for specific prompt patterns.
