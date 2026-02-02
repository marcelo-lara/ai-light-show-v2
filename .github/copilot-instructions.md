# AI Light Show v2 – Copilot Instructions

## Big-picture architecture
- Backend is FastAPI + asyncio in [backend/main.py](backend/main.py); it wires `StateManager`, `ArtNetService`, `SongService`, and `WebSocketManager` at startup and exposes only a WebSocket at `/ws`.
- Real-time DMX flow: frontend sends WebSocket messages → `WebSocketManager.handle_message()` → `StateManager` updates → `ArtNetService` sends ArtDMX UDP packets (see [backend/api/websocket.py](backend/api/websocket.py) and [backend/services/artnet.py](backend/services/artnet.py)).
- UI is Preact + Vite (WaveSurfer.js) in [frontend/src/App.jsx](frontend/src/App.jsx) and components under [frontend/src/components](frontend/src/components); it connects to `ws://localhost:8000/ws` and drives cue/fixture edits.

## Message protocol (WebSocket)
- `initial`: sent on connect with `fixtures`, `cues`, `song` (see `send_initial_state`).
- `delta`: `{type:"delta", channel, value}` updates a DMX channel and is broadcast to all clients.
- `timecode`: `{type:"timecode", time}` updates playback time; cues fire if within 0.1s (see `update_timecode`).
- `add_cue`: `{type:"add_cue", time, name}` captures current fixture values into a cue.
- `load_song`: `{type:"load_song", filename}` loads song metadata + cue sheet and re-sends initial state.
- `chat`: mock echo response only (see [backend/api/websocket.py](backend/api/websocket.py)).

## Domain data + storage
- Fixtures are defined in JSON at [backend/fixtures/fixtures.json](backend/fixtures/fixtures.json) and loaded on backend startup.
- Cues are stored per song in [backend/cues](backend/cues) as `{song}.cue.json` (written by `StateManager.save_cue_sheet()`).
- Song metadata lives in [backend/metadata](backend/metadata) as `{song}.metadata.json` and is loaded by `SongService`.

## Developer workflows
- Local dev: backend in [backend/main.py](backend/main.py) (`python main.py`) and frontend via Vite (`npm run dev`) per [README.md](README.md).
- Docker compose runs both services; frontend at http://localhost:3000, backend at http://localhost:8000 (see [README.md](README.md)).

## Project-specific conventions
- DMX channels are 1-based in messages and fixtures; `StateManager` stores a 0-based list of length 512.
- `ArtNetService` continuously sends frames at 60 FPS to `ARTNET_IP`/`ARTNET_PORT` in [backend/services/artnet.py](backend/services/artnet.py).
- Startup “arm” behavior uses `fixture.arm` values to preset channels before sending (see `arm_fixture`).
- Cue creation captures **current** fixture channel values from the DMX universe, not from UI state.

## Integration points
- Art-Net UDP packet format is hand-built in [backend/services/artnet.py](backend/services/artnet.py).
- Frontend WaveSurfer is initialized in [frontend/src/components/WaveformHeader.jsx](frontend/src/components/WaveformHeader.jsx); song loading is a placeholder (no REST endpoint yet).
