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

2a. Running tests

   - Use the `ai-light` Python environment (pyenv virtualenv) so tests can import backend modules. Example commands:

     ```bash
     # Use the pyenv-managed ai-light environment, then run tests with PYTHONPATH pointing at the backend package
     PYTHONPATH=./backend $(pyenv which python) -m pytest -q

     # Or, if your shell already activates the ai-light venv, a simpler form works:
     PYTHONPATH=./backend python -m pytest -q
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

Arm fixtures by setting "arm" channels and values from fixtures.json

## Workflow

1. Load song via frontend.
2. Adjust fixture sliders, deltas sent to backend.
3. Use the Cue Sheet editor to add cues at the desired timecode.
4. Playback syncs cues with audio.