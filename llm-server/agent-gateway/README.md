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

## Module layout

- `main.py`: thin entrypoint and test-facing re-export surface.
- `app.py`: FastAPI routes plus sync and streaming completion orchestration.
- `config.py`: environment variables, tool declarations, and MCP tool mapping.
- `gateway_models.py`: request model definitions used by the HTTP layer.
- `gateway_mcp/client.py`: backend MCP transport and tool dispatch.
- `gateway_mcp/arguments.py`: shared MCP argument helpers.
- `interpretation/*`: structured slot extraction and deterministic resolution before the generic tool loop.
- `rendering/results.py`: tool-result formatting and render dispatch.
- `prompt/guidance.py`: query-specific tool-routing guidance injection.
- `prompt/lookup_answers.py`: follow-up answer builders for section, chord, and cursor grounding.
- `prompt/factual_answers.py`: follow-up answer builders for cue-window, loudness, and fixture facts.
- `fast_path/extractors/*`: prompt parsing and fixture, section, chord, POI, timing, and effect helpers.
- `fast_path/answer_text.py`: deterministic text answers that do not require a follow-up model turn.
- `fast_path/proposals.py`: proposal payload construction and summary text.
- `fast_path/handlers/*`: grouped deterministic handlers for informational answers, cue proposals, movement proposals, and chaser proposals.
- `fast_path/router.py`: ordered fast-path orchestration.

## Fast-path assistant behavior

The gateway also performs deterministic fast-path handling for common assistant requests before relying on a follow-up model turn.

For prompts that are not handled by a deterministic fast path, the gateway can run a structured extraction stage before the generic tool loop. The first implemented slice extracts section timing slots from the prompt, resolves them against backend section metadata, and then asks the model to answer only from the resolved facts.

- Whole-sheet cue clear phrases resolve to a dedicated clear-all proposal instead of a synthetic `0..0` time window.
- Chord-conditioned edit prompts for prisms, parcans, and protons resolve to grounded cue-add proposals using backend metadata and fixture lists.
- Explicit-time cue edits such as `blue flash parcan_l at second 1.36` or `set both prisms to full at 0.00s` resolve to grounded cue-add proposals using fixture lookup plus beat lookup when the duration is specified in beats or defaults to one beat.
- POI-conditioned movement prompts such as moving a prism to piano before a named section resolve through section timing, beat lookup, fixture lookup, and POI lookup before producing a cue-add proposal.
- POI transition prompts for prism `orbit` and `sweep` effects resolve when the prompt provides an ordered POI path such as `from table to piano` or `from table to piano to sofa`.
- `none` chord spans are resolved from analyzer label `N` and can produce `blackout` or `fade_out` cue proposals across the full span.
- Factual prompts for prism effects, available POIs, section count, chords in a bar, cursor position, current section plus next beat, loudest section, and left-side fixtures resolve to deterministic grounded answers without a follow-up model turn.
- Write-capable turns stop at proposal generation so backend can require explicit confirmation before mutating cues.

## Response shaping

- Grounded timing answers prefer `bar.beat (seconds)` when tool results provide both values.
- The default assistant prompt avoids repeating the loaded song name unless the user explicitly asks for it.
- Proposal summaries preserve effect names where the distinction matters, including `blackout` and `fade_out`.

## MCP transport behavior

Implemented in `gateway_mcp/client.py` via `fastmcp.Client` against a Streamable HTTP MCP endpoint.

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
