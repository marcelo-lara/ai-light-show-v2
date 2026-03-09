# AI Light Show v2 - Copilot Instructions

## Development policy
- **NEVER keep deprecated code.** Remove deprecated helpers and dead code; do not retain compatibility shims.
- **NEVER prioritize backward compatibility over correctness.** Breaking changes are acceptable when they improve clarity and behavior.
- **ALWAYS use the `ai-light` Python environment** for local Python development.

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
- Frontend module guide: [frontend/README.md](../frontend/README.md)
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
- Analyzer scripts produce metadata under `analyzer/meta/<song>/...`; backend reads from `/app/meta` in Docker.
- LLM integration stack: local llama.cpp server + OpenAI-compatible agent gateway + MCP song metadata service.

## Playback model (DMX canvas)
- Cue sheets are **effect-based**: each entry contains `time`, `fixture_id`, `effect`, `duration`, `data` (see [backend/models/cue.py](../backend/models/cue.py)).
- On song load the backend renders a precomputed `60 FPS` DMX canvas for the song window (see [backend/store/dmx_canvas.py](../backend/store/dmx_canvas.py), [backend/store/state.py](../backend/store/state.py)).
- Client audio time is authoritative for sync; backend maps timecode to nearest frame.
- Fixture classes own effect math via `render_effect(...)` in [backend/models/fixtures](../backend/models/fixtures).

## Message protocol (WebSocket)
- **Client -> Backend:** `hello`, `intent`
- **Backend -> Client:** `snapshot`, `patch`, `event`
- While playing, backend sets `system.edit_lock=true` and rejects preview effects.
- `fixture.set_values` still applies channel updates in current implementation.
- Preview effects are backend-executed and non-persistent.

## Domain data + storage
- Fixtures: [backend/fixtures/fixtures.json](../backend/fixtures/fixtures.json)
- POIs: [backend/fixtures/pois.json](../backend/fixtures/pois.json)
- Cues: [backend/cues](../backend/cues) as `{song}.cue.json`
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
