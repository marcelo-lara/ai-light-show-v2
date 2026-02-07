# AI Light Show v2 — Architecture

AI Light Show v2 has three main modules:

- Frontend: audio playback + authoring UI.
- Backend: DMX canvas renderer + Art-Net output + WebSocket control plane.
- Analyzer: offline/async song analysis pipeline (Celery worker).

## How the modules interact

### Real-time playback loop

1. Frontend plays audio and sends `{type:"timecode", time:<seconds>}` while playing.
2. Backend maps time → frame index and selects the nearest precomputed DMX canvas frame.
3. Backend’s Art-Net service continuously emits `output_universe` at ~60 FPS.

### Authoring loop (paused)

1. Frontend sends live `{type:"delta", channel, value}` while editing.
2. Backend updates the editor universe (and output universe when paused).
3. Backend broadcasts `delta` to keep UIs in sync.

### Analysis loop (async)

1. Frontend requests analysis: `{type:"analyze_song", filename, ...}`.
2. Backend enqueues a Celery task and returns `{type:"task_submitted", task_id}`.
3. Worker runs analyzer pipeline and updates Celery meta (and optionally Redis pub/sub).
4. Backend polls task meta and broadcasts `analyze_progress` / `analyze_result`.

## Module docs

- Frontend: `docs/architecture/frontend.md`
- Backend: `docs/architecture/backend.md`
- Analyzer: `docs/architecture/analyzer.md`

## WebSocket protocol (canonical)

Backend → Frontend:

- `initial`: `{ fixtures, cues, song, playback:{ fps, songLengthSeconds, isPlaying } }`
- `delta`: `{ channel, value }`
- `dmx_frame`: `{ time, values }` (paused seek-preview)
- `cues_updated`: `{ cues }`
- `analyze_progress`: `{ task_id, state, meta }`
- `analyze_result`: `{ task_id, state, result }`

Frontend → Backend:

- `delta`
- `timecode`
- `seek`
- `playback`
- `add_cue`
- `load_song`
- `analyze_song`
- `chat`

