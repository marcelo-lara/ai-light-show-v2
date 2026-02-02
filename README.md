# AI Light Show v2

A real-time DMX control system synchronized with audio playback.

## Architecture

- **Backend**: Python/FastAPI with asyncio, ArtNet UDP dispatcher, WebSocket API, in-memory state management.
- **Frontend**: PReact with Vite, WaveSurfer.js for audio, real-time UI updates.

## Setup

### Local Development

1. Backend:
   ```bash
   cd backend
   python -m venv ai-light
   source ai-light/bin/activate  # or pyenv local ai-light
   pip install -r requirements.txt
   python main.py
   ```

2. Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Open http://localhost:5173

### Docker

```bash
docker compose up --build
```

Frontend on http://localhost:5000, backend on port 5001.

## Configuration

- ArtNet IP: 192.168.10.221
- Port: 6454
- FPS: 60

## Fixtures

Defined in `backend/fixtures/fixtures.json`.

Arm fixtures by setting dim to 255 before emitting light.

## Workflow

1. Load song via frontend.
2. Adjust fixture sliders, deltas sent to backend.
3. Click "Add to Cue" to save at current timecode.
4. Playback syncs cues with audio.