# AI Light Show v2

Real-time DMX show control with audio-synced playback, fixture-first editing, and Art-Net output.

## Current architecture

- **Backend**: FastAPI + asyncio service with a single WebSocket API at `/ws`.
- **State core**: `StateManager` maintains fixtures, cue sheet, editor/output universes, playback status, and precomputed DMX canvas.
- **Output**: `ArtNetService` continuously sends the current output universe at 60 FPS.
- **Frontend**: Preact + Vite app with a persistent shell (left menu, center content, right player/chat).
- **Analyzer**: Manual scripts producing song metadata files under `analyzer/meta/<song>/info.json`.

## Runtime behavior (important)

- Audio timeline is frontend-authoritative.
- While playing, backend output follows the song DMX canvas.
- While playing, **manual edits and preview are disabled**.
- While paused, manual edits (`delta`) can drive output directly.
- Effect preview (`preview_effect`) renders a temporary in-memory canvas and sends it live to Art-Net without persistence.
- Default startup song target is `Yonaka - Seize the Power` (falls back to first available song).

## Local development

1. Run analyzer scripts manually to generate metadata:

   ```bash
   cd analyzer
   python analyze_song.py /path/to/song.mp3
   ```

2. Backend

   ```bash
   cd backend
   python -m venv ai-light
   source ai-light/bin/activate
   pip install -r requirements.txt
   python main.py
   ```

3. Frontend

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. App URL

   - Frontend dev server: http://localhost:5173

## Tests

Use the `ai-light` Python environment and include both repository root and backend package on `PYTHONPATH`:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q
```

After each test run, rebuild/restart containers before the next live/manual validation:

```bash
docker compose down && docker compose up --build -d
```

## Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:5000
- Backend: http://localhost:5001
- Analyzer: manual runs via `docker compose run analyzer python analyze_song.py /app/songs/song.mp3`

## Art-Net debug mode

You can dump every sent DMX frame from `ArtNetService` for debugging.

- `ARTNET_DEBUG=1` enables frame dumping.
- `ARTNET_DEBUG_FILE=/path/to/artnet.log` writes dumps to a file (otherwise dumps to terminal).

Examples:

```bash
# terminal dump
ARTNET_DEBUG=1 python backend/main.py

# file dump
ARTNET_DEBUG=1 ARTNET_DEBUG_FILE=./artnet-debug.log python backend/main.py
```

## Fixture/effect synchronization rule

When backend fixture effects are added, removed, renamed, or their parameter contracts change, update:

- `frontend/src/components/dmx/effectPreviewConfig.js`

in the same change so preview effect options and parameter forms stay aligned.

## Key docs

- Architecture overview: `docs/architecture.md`
- Backend architecture: `docs/architecture/backend.md`
- Frontend architecture: `docs/architecture/frontend.md`
- UI behavior: `docs/ui/UI.md`