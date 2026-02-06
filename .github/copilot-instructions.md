# AI Light Show v2 – Copilot Instructions
## Development policy
- **NEVER keep deprecated code.** Remove deprecated helpers and dead code; do not retain compatibility shims.
- **NEVER consider backwards compatibility.** Breaking changes are acceptable — prefer clarity and correctness over preserving legacy APIs.
## Big-picture architecture
- Backend is FastAPI + asyncio in [backend/main.py](backend/main.py); it wires `StateManager`, `ArtNetService`, `SongService`, and `WebSocketManager` at startup and exposes only a WebSocket at `/ws`.
- Real-time DMX flow: frontend sends WebSocket messages → `WebSocketManager.handle_message()` → `StateManager` updates → `ArtNetService` sends ArtDMX UDP packets (see [backend/api/websocket.py](backend/api/websocket.py), [backend/store/state.py](backend/store/state.py), and [backend/services/artnet.py](backend/services/artnet.py)).
- UI is Preact + Vite (WaveSurfer.js) in [frontend/src/App.jsx](frontend/src/App.jsx) and components under [frontend/src/components](frontend/src/components); it connects to `ws://localhost:8000/ws` and drives cue/fixture edits.

## Playback model (DMX canvas)
- Cue sheets are **action-based** (not snapshot-only): each entry has `time`, `fixture_id`, `action`, `duration`, `data` (see [backend/models/cue.py](backend/models/cue.py)).
- On song load the backend renders a **precomputed 60 FPS DMX canvas** for the full song length (max 6 minutes) and stores it in memory (see [backend/store/dmx_canvas.py](backend/store/dmx_canvas.py) and [backend/store/state.py](backend/store/state.py)).
- The frontend audio timeline is authoritative; the backend selects the nearest canvas frame for a given timecode or seek.
- Fixture types own effect math via `Fixture.render_effect(...)` implemented in subclasses (see [backend/models/fixtures](backend/models/fixtures)).

## Message protocol (WebSocket)
- `initial`: sent on connect with `fixtures`, `cues`, `song`, and `playback` (see `send_initial_state` in [backend/api/websocket.py](backend/api/websocket.py)).
- `delta`: `{type:"delta", channel, value}` updates the editor DMX state and is broadcast.
	- While playing, backend **ignores deltas for output** (authoring edits are still recorded when you add cues).
- `timecode`: `{type:"timecode", time}` selects the nearest DMX canvas frame and updates Art-Net output.
- `seek`: `{type:"seek", time}` explicit jump; backend selects the correct frame immediately (frame skipping allowed).
- `playback`: `{type:"playback", playing}` toggles backend playback state (used to ignore live edits during playback).
- `add_cue`: `{type:"add_cue", time, name}` records actions into the cue sheet (currently `set_channels` per fixture).
- `cues_updated`: broadcast after cue changes with the full cue sheet.
- `load_song`: `{type:"load_song", filename}` loads song metadata + cue sheet, rebuilds the canvas, and re-sends initial state.
- `chat`: mock echo response only.

## Domain data + storage
- Fixtures are defined in JSON at [backend/fixtures/fixtures.json](backend/fixtures/fixtures.json) and loaded on backend startup.
- Cues are stored per song in [backend/cues](backend/cues) as `{song}.cue.json` (written by `StateManager.save_cue_sheet()`), using the action-based schema.
- Song metadata lives in [backend/metadata](backend/metadata) as `{song}.metadata.json` and is loaded by `SongService`.

## Developer workflows
- Local dev: backend in [backend/main.py](backend/main.py) (`python main.py`) and frontend via Vite (`npm run dev`) per [README.md](README.md).
- Run tests locally using the `ai-light` Python environment (pyenv virtualenv). Example:

  ```bash
  PYTHONPATH=./backend $(pyenv which python) -m pytest -q
  ```

- Docker compose runs both services; frontend at http://localhost:3000, backend at http://localhost:8000 (see [README.md](README.md)).

## Project-specific conventions
- DMX channels are 1-based in messages and fixtures; `StateManager` stores a 0-based list of length 512.
- `ArtNetService` sends frames at 60 FPS to `ARTNET_IP`/`ARTNET_PORT` in [backend/services/artnet.py](backend/services/artnet.py).
- Startup “arm” behavior uses `fixture.arm` values to preset channels before sending (see `arm_fixture`).

## Canonical architecture doc
- See [docs/architecture.md](docs/architecture.md) for the detailed, up-to-date architecture.

## Integration points
- Art-Net UDP packet format is hand-built in [backend/services/artnet.py](backend/services/artnet.py).
- Frontend WaveSurfer is initialized in [frontend/src/components/WaveformHeader.jsx](frontend/src/components/WaveformHeader.jsx); song loading is a placeholder (no REST endpoint yet).
