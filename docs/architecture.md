# AI Light Show v2 — Architecture

AI Light Show v2 has three main modules:

- Frontend: audio playback + authoring UI.
- Backend: DMX canvas renderer + Art-Net output + WebSocket control plane.
- Analyzer: offline song analysis scripts producing metadata files.

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

### Analysis loop (manual)

1. User runs analyzer scripts manually to produce metadata files under `analyzer/meta/<song>/info.json`.
2. Frontend requests metadata reload: `{type:"reload_metadata"}` (or similar UI action).
3. Backend reloads metadata from `/app/meta` and rebroadcasts initial state with updated song data.

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

Frontend → Backend:

- `delta`
- `timecode`
- `seek`
- `playback`
- `preview_effect`
- `add_cue`
- `load_song`
- `chat`

## Reference
In the xLights ecosystem, there are several file extensions you will encounter. Each serves a specific purpose in the workflow—from design and sequencing to the final "rendered" output you are interested in.

.fseq (Falcon Sequence): This is the primary rendered file. 
When you "Save" or "Render All" in xLights, it generates this binary file. 
It maps every channel to a byte value (0–255) for every frame (20, 40 or 55 FPS). 
It is designed to be played by FPP (Falcon Pi Player) or uploaded directly to controllers.

Summary Table for Quick Reference

| Extension | Type | Content |
| --- | --- | --- |
| .fseq | Binary (Rendered) | Raw byte arrays for Art-Net/DMX output.
| .xsq | XML (Source) | The sequence timeline and effect settings.
| .xml | XML (Config) | The hardware controller and prop layout settings.
| .eseq | Binary (Effect) | Byte arrays for a single model/prop only.