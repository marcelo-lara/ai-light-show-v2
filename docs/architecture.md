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

### Preview loop (paused only)

1. Frontend sends `{type:"preview_effect", fixture_id, effect, duration, data}`.
2. Backend rejects if playback is active.
3. If accepted, backend renders a temporary in-memory preview canvas and drives Art-Net from it.
4. Backend broadcasts `preview_status` and global `status` updates; preview is never persisted to cues/files.

### Analysis loop (async)

1. Frontend requests analysis: `{type:"analyze_song", filename, ...}`.
2. Backend enqueues a Celery task and returns `{type:"task_submitted", task_id}`.
3. Worker runs analyzer pipeline and updates Celery meta (and optionally Redis pub/sub).
4. Backend polls task meta and broadcasts `analyze_progress` / `analyze_result`.

### Meta source (Docker)

- In Docker, backend reads song meta from `/app/meta` (mounted from `analyzer/meta`).
- If `/app/meta` is unavailable, backend falls back to local `backend/meta`.
- Backend accepts analyzer-style per-song JSON directories and song-level JSON files in the meta root.

## Module docs

- Frontend: `docs/architecture/frontend.md`
- Backend: `docs/architecture/backend.md`
- Analyzer: `docs/architecture/analyzer.md`

## WebSocket protocol (canonical)

Backend → Frontend:

- `initial`: `{ fixtures, cues, song, playback:{ fps, songLengthSeconds, isPlaying }, status }`
- `delta`: `{ channel, value }`
- `delta_rejected`: `{ reason }` (when playback is active)
- `dmx_frame`: `{ time, values }` (paused seek-preview)
- `cues_updated`: `{ cues }`
- `status`: `{ status:{ isPlaying, previewActive, preview? } }`
- `preview_status`: `{ active, request_id, fixture_id?, effect?, duration?, reason? }`
- `analyze_progress`: `{ task_id, state, meta }`
- `analyze_result`: `{ task_id, state, result }`
- `task_submitted`: `{ task_id }`
- `task_error`: `{ task_id?, message }`

Frontend → Backend:

- `delta`
- `timecode`
- `seek`
- `playback`
- `preview_effect`
- `add_cue`
- `load_song`
- `analyze_song`
- `chat`

