# AI Light Show v2 - Copilot Instructions

## Development policy
- **NEVER keep deprecated code.** Remove deprecated helpers and dead code; do not retain compatibility shims.
- **NEVER prioritize backward compatibility over correctness.** Breaking changes are acceptable when they improve clarity and behavior.
- **ALWAYS use the `ai-light` Python environment** for local Python development.

## LLM code size and quality rules
- Prefer small files: target `<= 100` lines per file.
- If a file would exceed `100` lines, split by responsibility into focused modules.
- Keep functions small and single-purpose.
- Favor pure functions for business logic; isolate side effects at boundaries.
- Use clear names, explicit types, and consistent return shapes.
- Avoid duplicated logic; extract reusable helpers.
- Add minimal comments only when intent is not obvious from code.
- Include basic validation and error handling at I/O and integration boundaries.
- Do not keep deprecated code or compatibility shims.
- If a rule conflicts with correctness, prioritize correctness and document the tradeoff in the PR/commit message.

Activate environment before Python work:

```bash
pyenv activate ai-light
```

If shell activation is unavailable, run commands through:

```bash
PYENV_VERSION=ai-light pyenv exec <command>
```

## Documentation map (use these first)
- Project overview: [README.md](../README.md)
- Canonical architecture index: [docs/architecture.md](../docs/architecture.md)
- Backend runtime/protocol source of truth: [docs/architecture/backend_llm_reference.md](../docs/architecture/backend_llm_reference.md)
- Frontend module guide (entrypoints/routes/intents/component map): [frontend/README.md](../frontend/README.md)
- UI docs + LoFi asset index: [docs/ui/README.md](../docs/ui/README.md)
- Backend module guide: [backend/README.md](../backend/README.md)
- Analyzer module guide: [analyzer/README.md](../analyzer/README.md)
- LLM stack guide: [llm-server/README.md](../llm-server/README.md)
- Agent gateway guide: [llm-server/agent-gateway/README.md](../llm-server/agent-gateway/README.md)
- MCP module guide: [mcp/README.md](../mcp/README.md)
- Song metadata MCP guide: [mcp/song_metadata/README.md](../mcp/song_metadata/README.md)
- Test module guide: [tests/README.md](../tests/README.md)

## Big-picture architecture
- Backend is FastAPI + asyncio in [backend/main.py](../backend/main.py); it wires `StateManager`, `ArtNetService`, `SongService`, and `WebSocketManager` at startup.
- Control plane is websocket `/ws`; state is emitted via `snapshot` and `patch` messages.
- Real-time DMX flow: client websocket messages -> intent handlers/state builders -> `StateManager` updates -> `ArtNetService` sends ArtDMX UDP packets.
- The UI frontend is strictly a backend client. DMX logic is backend-owned.
- Active frontend routes are `show_control`, `song_analysis`, `show_builder`, and `dmx_control` (see [frontend/src/app/routes.ts](../frontend/src/app/routes.ts)).
- Analyzer scripts produce metadata under `analyzer/meta/<song>/...`; backend reads from `/app/meta` in Docker.
- LLM integration stack: local llama.cpp server + OpenAI-compatible agent gateway + MCP song metadata service.

## Playback model (DMX canvas)
- Cue sheets use a mixed schema:
  - effect row: `time`, `fixture_id`, `effect`, `duration`, `data`
  - chaser row: `time`, `chaser_id`, `data`
- On song load the backend renders a precomputed `60 FPS` DMX canvas for the song window (see [backend/store/dmx_canvas.py](../backend/store/dmx_canvas.py), [backend/store/state.py](../backend/store/state.py)).
- Client audio time is authoritative for sync; backend maps timecode to nearest frame.
- Fixture classes own effect math via `render_effect(...)` in [backend/models/fixtures](../backend/models/fixtures).
- Chaser cue rows persist by `chaser_id` and expand into effect renders only at canvas/preview time.

## Message protocol (WebSocket)
- **Client -> Backend:** `hello`, `intent`
- **Backend -> Client:** `snapshot`, `patch`, `event`
- While playing, backend sets `system.edit_lock=true` and rejects preview effects.
- `fixture.set_values` still applies channel updates in current implementation.
- Preview effects are backend-executed and non-persistent.

## Domain data + storage
- Fixtures: [backend/fixtures/fixtures.json](../backend/fixtures/fixtures.json)
- POIs: [backend/fixtures/pois.json](../backend/fixtures/pois.json)
- Cues: [backend/cues](../backend/cues) as `{song}.json`
- Song metadata: analyzer output at `analyzer/meta/<song>/info.json`, loaded by backend during song load

## Developer workflows
- Run backend locally from [backend/main.py](../backend/main.py).
- Activate env before Python commands:

  ```bash
  pyenv activate ai-light
  ```

- Run tests:

  ```bash
  PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q
  ```

- After local test runs, rebuild/restart containers before live/manual validation:

  ```bash
  docker compose down && docker compose up --build -d
  ```

## Project-specific conventions
- DMX channels are 1-based in fixture/message contracts; runtime storage uses 512-byte arrays.
- `ArtNetService` sends at `60 FPS` to configured `ARTNET_IP`/`ARTNET_PORT`.
- Startup arm behavior applies configured fixture arm values.
- Whenever fixture effect contracts change, update backend docs and active client integration in the same change.
- For frontend UI implementation:
  - Prefer flexbox over grid for small/local components.
  - DO NOT CREATE BORDERS unless explicitly requested.
  - NEVER EVER USE ROUNDED CORNERS.
  - LoFi mockups are layout references only; do not reinterpret their intended layout.
  - Never render annotation/instruction text from mockups in the final UI.
  - Never copy annotation colors (for example pink guidance text) into production UI.
  - Do not implement explicit mockup dimensions or colors directly; use responsive sizing and existing theme tokens/variables.
  - Use CUBE CSS naming and structure; do not introduce BEM class patterns (`__`, `--`) in frontend code.
  - CUBE model in this repo: Composition uses `l-`/`o-`, Utilities use `u-`, Blocks use semantic component names, Exceptions use `is-`/`has-`.
  - Keep components plain: avoid wrapper-over-wrapper nesting unless required for semantics, accessibility, or behavior.
  - Do not add padding or gap values unless explicitly required by the task or LoFi constraints.
  - In `frontend/src/features`, use shared themed controls (`Button`, `Dropdown`, `Slider`, `Toggle`) instead of creating raw `button`, `select`, `input[type=range]`, or `input[type=checkbox]` elements.
  - Avoid feature-local custom styling variants for those controls; extend shared control components/tokens when behavior or appearance changes are needed.
  - Keep feature CSS layout-focused; do not style shared control internals from feature files (`.btn`, `.btn-content`, `.input-shell`, `.input-field`, `.dropdown`, `.toggle`, `.slider-row`).
  - Keep state visuals shared: use `.is-active` and `.is-selected` from `frontend/src/app/themes.css`; do not create feature-specific selected/active visual variants.
  - For destructive actions (for example deleting cues), use `frontend/src/shared/components/feedback/ConfirmCancelPrompt.ts` instead of direct delete execution.
  - For rows combining cue/info text and actions, use a two-column flex layout with right-aligned action group.
  - Use the reusable prompt in [frontend/README.md](../frontend/README.md) section `LLM UI Task Template` for layout tasks.

## Documentation update rule
- If you change architecture, protocol, ports, module responsibilities, workflows, data shapes, or intent/event behavior, update relevant docs in the same change.
- For backend/runtime changes, update at minimum:
  - [backend/README.md](../backend/README.md)
  - [docs/architecture/backend.md](../docs/architecture/backend.md)
  - [docs/architecture/backend_llm_reference.md](../docs/architecture/backend_llm_reference.md)
- Write documentation as current-state behavior only.
- Do not use change-history wording such as: `refactor`, `new`, `legacy`, `old`, `before`, `after`.

## Integration points
- Art-Net packet build/send: [backend/services/artnet.py](../backend/services/artnet.py)
- WebSocket manager: [backend/api/websocket_manager](../backend/api/websocket_manager)
- Intent dispatch: [backend/api/intents](../backend/api/intents)
