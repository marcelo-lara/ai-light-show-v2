# AI Light Show v2 — Architecture

AI Light Show v2 has two main modules:

- Frontend: audio playback + authoring UI.
- Backend: DMX canvas renderer + Art-Net output + WebSocket control plane.

## How the modules interact

### Real-time playback loop

1. Frontend plays audio and sends `{type:"timecode", time:<seconds>}` while playing.
2. Backend maps time → frame index and selects the nearest precomputed DMX canvas frame.
3. Backend’s Art-Net service continuously emits `output_universe` at ~60 FPS.

### Authoring loop (paused)

1. Frontend sends live `{type:"delta", channel, value}` while editing.
2. Backend updates the editor universe (and output universe when paused).
3. Backend broadcasts `delta` to keep UIs in sync.

## Module docs

- Frontend: `docs/architecture/frontend.md`
- Backend: `docs/architecture/backend.md`

## WebSocket protocol (canonical)

Backend → Frontend:

- `initial`: `{ fixtures, cues, song, playback:{ fps, songLengthSeconds, isPlaying } }`
- `delta`: `{ channel, value }`
- `dmx_frame`: `{ time, values }` (paused seek-preview)
- `cues_updated`: `{ cues }`

Frontend → Backend:

- `delta`
- `timecode`
- `seek`
- `playback`
- `add_cue`
- `load_song`
- `chat`
