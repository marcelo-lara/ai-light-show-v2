# AI Light Show v2 – Copilot Instructions
## Development policy
- **NEVER keep deprecated code.** Remove deprecated helpers and dead code; do not retain compatibility shims.
- **NEVER consider backwards compatibility.** Breaking changes are acceptable — prefer clarity and correctness over preserving legacy APIs.

## Documentation map (use these first)
- Project overview: [README.md](../README.md)
- Canonical architecture index: [docs/architecture.md](../docs/architecture.md)
- Backend module guide: [backend/README.md](../backend/README.md)
- Frontend module guide: [frontend/README.md](../frontend/README.md)
- Analyzer module guide: [analyzer/README.md](../analyzer/README.md)
- LLM stack guide: [llm-server/README.md](../llm-server/README.md)
- Agent gateway guide: [llm-server/agent-gateway/README.md](../llm-server/agent-gateway/README.md)
- MCP module guide: [mcp/README.md](../mcp/README.md)
- Song metadata MCP guide: [mcp/song_metadata/README.md](../mcp/song_metadata/README.md)
- Test module guide: [tests/README.md](../tests/README.md)

## Big-picture architecture
- Backend is FastAPI + asyncio in [backend/main.py](../backend/main.py); it wires `StateManager`, `ArtNetService`, `SongService`, and `WebSocketManager` at startup and exposes only a WebSocket at `/ws`.
- Real-time DMX flow: frontend sends WebSocket messages → `WebSocketManager.handle_message()` → `StateManager` updates → `ArtNetService` sends ArtDMX UDP packets (see [backend/api/websocket.py](../backend/api/websocket.py), [backend/store/state.py](../backend/store/state.py), and [backend/services/artnet.py](../backend/services/artnet.py)).
- UI is Preact + Vite + preact-router + WaveSurfer. Entry is [frontend/src/App.jsx](../frontend/src/App.jsx); shared state + WebSocket logic lives in [frontend/src/app/state.jsx](../frontend/src/app/state.jsx); routed pages are under [frontend/src/pages](../frontend/src/pages). The UI uses a persistent app shell with a left icon menu and a right panel (player + chat).
- Analyzer: manual scripts producing song metadata files under `analyzer/meta/<song>/info.json`; backend loads from `/app/meta` (mounted from `analyzer/meta` in Docker).
- LLM integration stack: local llama.cpp server + OpenAI-compatible agent gateway + MCP song metadata service (see [llm-server/README.md](../llm-server/README.md), [llm-server/agent-gateway/README.md](../llm-server/agent-gateway/README.md), [mcp/song_metadata/README.md](../mcp/song_metadata/README.md), and [CODEX_INSTRUCTIONS.md](../CODEX_INSTRUCTIONS.md)).

## Playback model (DMX canvas)
- Cue sheets are **action-based** (not snapshot-only): each entry has `time`, `fixture_id`, `action`, `duration`, `data` (see [backend/models/cue.py](../backend/models/cue.py)).
- On song load the backend renders a **precomputed 60 FPS DMX canvas** for the full song length (max 6 minutes) and stores it in memory (see [backend/store/dmx_canvas.py](../backend/store/dmx_canvas.py) and [backend/store/state.py](../backend/store/state.py)).
- The frontend audio timeline is authoritative; the backend selects the nearest canvas frame for a given timecode or seek.
- Fixture types own effect math via `Fixture.render_effect(...)` implemented in subclasses (see [backend/models/fixtures](../backend/models/fixtures)).

## Message protocol (WebSocket)
- `initial`: sent on connect with `fixtures`, `cues`, `song`, `playback`, and `status` (see `send_initial_state` in [backend/api/websocket.py](../backend/api/websocket.py)).
- `delta`: `{type:"delta", channel, value}` updates the editor DMX state and is broadcast.
  - While playing, backend rejects deltas (`delta_rejected`) and does not apply authoring edits.
- `timecode`: `{type:"timecode", time}` selects the nearest DMX canvas frame and updates Art-Net output.
- `seek`: `{type:"seek", time}` explicit jump; backend selects the correct frame immediately (frame skipping allowed).
- `playback`: `{type:"playback", playing}` toggles backend playback state (used to ignore live edits during playback).
- `status`: backend broadcast with global state `{isPlaying, previewActive, preview}`.
- `preview_effect`: `{type:"preview_effect", fixture_id, effect, duration, data}` triggers temporary preview render when paused.
- `preview_status`: backend broadcast with preview lifecycle (`active`, `request_id`, optional reason/details).
- `add_cue`: `{type:"add_cue", time, name}` records actions into the cue sheet (currently `set_channels` per fixture).
- `cues_updated`: broadcast after cue changes with the full cue sheet.
- `load_song`: `{type:"load_song", filename}` loads song metadata + cue sheet, rebuilds the canvas, and re-sends initial state.
- `chat`: mock echo response only.

## Domain data + storage
- Fixtures are defined in JSON at [backend/fixtures/fixtures.json](../backend/fixtures/fixtures.json) and loaded on backend startup.
- Cues are stored per song in [backend/cues](../backend/cues) as `{song}.cue.json` (written by `StateManager.save_cue_sheet()`), using the action-based schema.
- Song metadata is produced offline by analyzer scripts (`analyzer/analyze_song.py`) and stored as `analyzer/meta/<song>/info.json`; backend loads this on startup or reload.
- Backend tracks `is_dirty` in memory for user edits (e.g., song sections); persisted only on explicit save via `save_sections` message.

## Developer workflows
- Local dev: backend in [backend/main.py](../backend/main.py) (`python main.py`) and frontend via Vite (`npm run dev`) per [README.md](../README.md).
- Run tests locally using the `ai-light` Python environment (pyenv virtualenv). Example:

  ```bash
  PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q
  ```

- After each test run, rebuild/restart Docker containers before any live/manual validation:

  ```bash
  docker compose down && docker compose up --build -d
  ```

- Full compose stack also includes LLM/MCP services: llama.cpp (`:8080`), agent-gateway (`:8090`), song-metadata-mcp (`:8089`) per [README.md](../README.md).
- Docker compose serves frontend at http://localhost:9000 and backend at http://localhost:5001 (see [README.md](../README.md)).

## Project-specific conventions
- DMX channels are 1-based in messages and fixtures; `StateManager` stores a 0-based list of length 512.
- `ArtNetService` sends frames at 60 FPS to `ARTNET_IP`/`ARTNET_PORT` in [backend/services/artnet.py](../backend/services/artnet.py).
- Startup “arm” behavior uses `fixture.arm` values to preset channels before sending (see `arm_fixture`).
- **LLM change requirement:** whenever any fixture effect is added, removed, renamed, or its parameter contract is changed in backend models/fixtures data, update [frontend/src/components/dmx/effectPreviewConfig.js](../frontend/src/components/dmx/effectPreviewConfig.js) in the same change so UI effect options and parameter forms stay in sync.

## Canonical architecture doc
- See [docs/architecture.md](../docs/architecture.md) for the detailed, up-to-date architecture.

## Documentation update rule
- If you change architecture, protocol, ports, module responsibilities, or workflows, update the relevant module README(s) and [README.md](../README.md) in the same change.

## Integration points
- Art-Net UDP packet format is hand-built in [backend/services/artnet.py](../backend/services/artnet.py).
- Frontend WaveSurfer is initialized in [frontend/src/components/player/WaveformHeader.jsx](../frontend/src/components/player/WaveformHeader.jsx); playback is controlled from the always-visible right-panel player via registered audio controls.
