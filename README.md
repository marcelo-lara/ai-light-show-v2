# AI Light Show v2

Real-time DMX show control with audio-synced playback, fixture-first editing, Art-Net output, and local LLM tooling.

## System architecture

AI Light Show is split into six primary modules:

- **frontend/**: Deno-served TypeScript client acting as a "dumb console" that maps user actions to backend intents.
- **backend/**: FastAPI + asyncio WebSocket server, DMX state/canvas engine, Art-Net sender.
- **analyzer/**: Offline metadata generation (`analyzer/meta/<song>/...`).
- **llm-server/agent-gateway/**: OpenAI-compatible gateway that translates model tool calls to MCP JSON-RPC.
- **tests/**: backend/analyzer integration and regression tests.

### Canonical runtime flow

1. Frontend connects to `/ws`, sends `hello`, and receives backend-authoritative `snapshot` + `patch` updates.
2. UI emits only `intent` messages; backend applies domain logic and rebroadcasts state deltas.
3. Backend selects nearest precomputed DMX canvas frame and updates Art-Net output.
4. Preview requests (`fixture.preview_effect`) render temporary in-memory output only (no persistence).
5. Analyzer writes song metadata; backend consumes it from `/app/meta` in Docker.
6. Backend exposes mounted MCP tools at `/mcp`; agent-gateway forwards LLM tool calls there.

### Important behavior constraints

- Client playback timeline is authoritative.
- Browser player owns real audio playback and local timecode.
- Frontend syncs timecode to backend every 10 seconds while playing, plus immediate sync on play/pause/seek/stop.
- While playing, backend enforces `system.edit_lock` and rejects preview requests.
- Cue sheets are action-based and rendered into a full 60 FPS DMX canvas on song load.
- Default startup song target is `Yonaka - Seize the Power` (fallback: first available).

## Module documentation (LLM-first)

- [frontend/README.md](frontend/README.md)
- [analyzer/README.md](analyzer/README.md)
- [backend/README.md](backend/README.md)
- [llm-server/README.md](llm-server/README.md)
- [tests/README.md](tests/README.md)

## Local development

### 1) Generate metadata (manual)

```bash
cd analyzer
python analyze_song.py /path/to/song.mp3
```

### 2) Run backend

```bash
cd backend
python -m venv ai-light
source ai-light/bin/activate
pip install -r requirements.txt
python main.py
```

- Backend API/WS URL: http://localhost:5001 (`/ws`)

## Docker

```bash
docker compose up --build
```

- Backend: http://localhost:5001
- Frontend: http://localhost:5173
- LLM server: http://localhost:8080
- Agent gateway: http://localhost:8090
- Analyzer: run manually via `docker compose run analyzer ...`

## Tests

Use the `ai-light` Python environment:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q
```

All automated Python tests live under `tests/`.

After test runs, rebuild/restart containers before manual validation:

```bash
docker compose down && docker compose up --build -d
```

## Art-Net debug mode

- `DEBUG_MODE=1` enables DMX frame logging to stdout when packets are sent.

```bash
DEBUG_MODE=1 python backend/main.py
```

## Cross-module change rule

When backend fixture effects are added, removed, renamed, or their parameters change, update protocol documentation and any active control client in the same change.

## Reference docs

- `docs/architecture.md`
- `docs/architecture/backend.md`
- `docs/architecture/analyzer.md`
- `docs/ui/UI_Future_state.md`
