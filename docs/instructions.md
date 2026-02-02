# AI Light Show v2 - Implementation Plan

## 1. System Overview
The AI Light Show v2 is a real-time DMX control system synchronized with audio playback. It uses a PReact frontend for the UI and a Python/FastAPI backend for DMX dispatching (ArtNet) and state management.

## 2. Backend Architecture
The backend is a service-oriented Python application that manages song data, DMX states, and ArtNet communication.

### 2.1 Directory Structure
```
backend/
├── main.py              # Entry point (FastAPI/Uvicorn)
├── api/
│   └── websocket.py     # WebSocket gateway (Deltas & Sync)
├── models/
│   ├── fixture.py       # Pydantic models for Fixtures
│   ├── cue.py           # Pydantic models for Cues
│   └── song.py          # Pydantic models for Song/Metadata
├── services/
│   ├── artnet.py        # Custom ArtNet UDP implementation
│   └── song_service.py  # File discovery and management
└── store/
    └── state.py         # In-memory StateManager (Thread-safe)
```

### 2.2 Data Conventions
- **Songs**: Located in `backend/songs/`.
- **Cues**: `backend/cues/[song-filename].cue.json`.
- **Metadata**: `backend/metadata/[song-filename].metadata.json`.
- **Fixtures**: Defined in `backend/fixtures/fixtures.json`.

### 2.3 Key Features
- **In-Memory State**: No database. Current DMX values, cues, and metadata are held in memory and flushed to JSON files on change.
- **ArtNet Dispatcher**: 
    - Sends 512-channel DMX frames over UDP. Packets are sent **immediately** upon value change, throttled at 60 FPS.
    - Custom implementation based on [reference implementation](docs/dmx_dispatcher.py) (don't use this file, NOT even as fallback)
- **DMX Fixtures**: 
    - DMX Lighting fixtures are [retrieved from this config file](backend/fixtures/fixtures.json)
    - A Fixture need to be "armed" before emit light: use the "arm" node to send the arm channel/values to the ArtNet node with the actual color and position data. For testing purposes, always set the "dim" values to 255.

- **WebSocket Protocol**:
    - **Initial Load**: Sends full state (fixtures, cues, metadata).
    - **Live Edits**: Sends only **deltas** (e.g., `{ "channel": 12, "value": 255 }`).
    - **Sync**: Timecode sync between frontend waveform and backend state.

## 3. Frontend Architecture
- The frontend is a PReact application built with Vite, emphasizing real-time interactivity.
- Signaling from backend and initial load must be ONLY using WebSockets. (ONLY mp3 song load could be API)
- The frontend skeleton layout is '![LoFi mockup](<docs/LoFi Layout Reference.png>)'; The user requested a Dark Themed of this layout.

### 3.1 Components
- **WaveformHeader**: Uses `wavesurfer.xyz` for audio playback and seeking.
- **Lanes Layout** (Three independently scrollable columns):
    - **SongPartsLane**: Markers for intro, verse, chorus, etc.
    - **CueSheetLane**: List of saved light snapshots.
    - **FixturesLane**: Sliders for individual fixture channels.
- **ChatSidePanel**: VS Code-like chat interface for LLM interaction (Backend currently mocks an echo websocket).

## 4. Workflows

### 4.1 Song Loading
1. User selects song from list.
2. Backend loads associated `.cue.json` and `.metadata.json`.
3. Backend broadcasts full state to all connected clients.
4. Frontend initializes Wavesurfer and populates lanes.

### 4.2 "Add to Cue"
1. User adjusts sliders in the **FixturesLane**.
2. Frontend sends delta updates to Backend via WebSocket.
3. Backend updates in-memory DMX buffer and sends ArtNet packet.
4. User clicks "Add to Cue".
5. Backend captures current DMX buffer at current `timecode`.
6. Entry added to in-memory `CueSheet` and saved to `[song].cue.json`.

## 5. Development Instructions
1. **Backend**:
   - Use `asyncio` for non-blocking UDP and WebSocket operations.
   - Implement `StateManager` with `asyncio.Lock`.
   - Mock LLM responses as a simple echo.
2. **Frontend**:
   - Install `wavesurfer.js`.
   - Use a lightweight state management (or PReact Context) for DMX values.
   - Maintain a 60 FPS reactive UI.
3. **Environment**:
   - ArtNet IP: `192.168.10.221`
   - Port: `6454`
   - Target FPS: `60`

## 6. Dockerization
The application runs as a multi-container setup using Docker Compose.

### 6.1 Backend (Dockerfile)
- **Base Image**: `python:3.11-slim`
- **Networking**: Uses `network_mode: host` to allow unrestricted UDP broadcasting for ArtNet packets to the DMX node.
- **Volumes**:
    - Mounts `./backend/songs` for audio storage.
    - Mounts `./backend/cues` and `./backend/metadata` for persistence.
- **Dependencies**: `fastapi`, `uvicorn`, `websockets`, `pydantic`.

### 6.2 Frontend (Dockerfile)
- **Base Image**: `node:20-alpine` (for build) and `nginx:alpine` (for serving).
- **Environment**: Needs `VITE_WS_URL` to point to the backend host.

### 6.3 Orchestration (docker-compose.yml)
- **Services**: `backend` and `frontend`.
- **Environment Variables**:
    - `DMX_NODE_IP`: `192.168.10.221`
    - `FPS`: `60`
- **Command**: `docker compose up --build`

## IMPORTANT NOTES

- DO NOT create CI actions to test on GitHub.
- When running locally use the "ai-light" Python virtual environment.
- If tests were performed, do it ONLY inside the docker environment.
- Update ".dockerignore" and ".gitignore" to avoid cache and external modules (ex: node_modules)