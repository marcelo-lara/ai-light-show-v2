# AI Light Show v2

Real-time DMX show control with audio-synced playback, fixture-first editing, Art-Net output, and local LLM tooling.

## System architecture

AI Light Show is split into six primary modules:

- **frontend/**: Deno-served TypeScript client acting as a "dumb console" that maps user actions to backend intents.
- **backend/**: FastAPI + asyncio WebSocket server, DMX state/canvas engine, Art-Net sender.
- **data/**: Canonical song audio, generated metadata, and analysis artifacts (`data/songs`, `data/output`, `data/artifacts`).
- **llm-server/agent-gateway/**: OpenAI-compatible gateway that translates model tool calls to MCP JSON-RPC.
- **tests/**: backend metadata, protocol, and regression tests.

### Canonical runtime flow

1. Frontend connects to `/ws`, sends `hello`, and receives backend-authoritative `snapshot` + `patch` updates.
2. UI emits only `intent` messages; backend applies domain logic and rebroadcasts state deltas.
3. Backend selects nearest precomputed DMX canvas frame and updates Art-Net output.
4. Preview requests (`fixture.preview_effect`) render temporary in-memory output only (no persistence).
5. Backend reads song audio from `/app/songs`, metadata from `/app/meta`, and artifact manifests from `/data/artifacts` in Docker.
6. Backend exposes mounted MCP tools at `/mcp`; agent-gateway forwards LLM tool calls there.

### Important behavior constraints

- Client playback timeline is authoritative.
- Browser player owns real audio playback and local timecode.
- Frontend keeps backend time aligned to the browser audio clock while playing using a short sync cadence, plus immediate sync on play/pause/seek/stop.
- While playing, backend enforces `system.edit_lock` and rejects preview requests.
- Cue sheets are action-based and rendered into a full 60 FPS DMX canvas on song load.
- Art-Net output is transmitted to the node at 30 FPS while the backend keeps the internal DMX canvas at 60 FPS.
- Default startup song target is `Yonaka - Seize the Power` when present (fallback: first available).

## Module documentation (LLM-first)

- [frontend/README.md](frontend/README.md)
- [backend/README.md](backend/README.md)
- [llm-server/README.md](llm-server/README.md)
- [tests/README.md](tests/README.md)

## Local development

### 1) Run backend

```bash
cd backend
PYENV_VERSION=ai-light pyenv exec pip install -r requirements.txt
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
- `docs/ui/UI_Future_state.md`
