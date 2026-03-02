# AI Light Show v2 — Architecture

## Start here for LLMs

Use these module guides first, then drill into architecture detail docs.

- Project overview: [../README.md](../README.md)
- Backend module: [../backend/README.md](../backend/README.md)
- Frontend module: [../frontend/README.md](../frontend/README.md)
- Analyzer module: [../analyzer/README.md](../analyzer/README.md)
- LLM server + gateway: [../llm-server/README.md](../llm-server/README.md)
- MCP services: [../mcp/README.md](../mcp/README.md)
- Tests module: [../tests/README.md](../tests/README.md)

AI Light Show v2 is split into six primary modules:

- Frontend: Preact UI, WaveSurfer playback, and WebSocket control client.
- Backend: FastAPI + asyncio WebSocket server, DMX state/canvas engine, Art-Net sender.
- Analyzer: offline metadata generation in `analyzer/meta/<song>/...`.
- MCP song metadata service: read-only metadata query tools over SSE.
- LLM agent gateway: OpenAI-compatible wrapper that maps tool calls to MCP JSON-RPC.
- Tests: analyzer/backend integration and regression coverage.

## How the modules interact

### Canonical runtime flow

1. Frontend drives playback timeline and sends `timecode` / `seek` / `playback` over `/ws`.
2. Backend selects nearest precomputed DMX canvas frame and updates Art-Net output.
3. While paused, frontend edits (`delta`) update editor/output universes directly.
4. Preview requests (`preview_effect`) render temporary in-memory output only (no persistence).
5. Analyzer writes song metadata and backend reads it from `/app/meta` in Docker.
6. MCP exposes metadata tools and the agent gateway forwards LLM tool calls.

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
2. Backend loads metadata on song load from `/app/meta` and rebroadcasts initial state.

### Meta source (Docker)

- In Docker, backend reads song meta from `/app/meta` (mounted from `analyzer/meta`).
- If `/app/meta` is unavailable, backend falls back to local `backend/meta`.
- Backend accepts analyzer-style per-song JSON directories and song-level JSON files in the meta root.

## Module docs

- Frontend module guide: [../frontend/README.md](../frontend/README.md)
- Backend module guide: [../backend/README.md](../backend/README.md)
- Analyzer module guide: [../analyzer/README.md](../analyzer/README.md)
- LLM stack guide: [../llm-server/README.md](../llm-server/README.md)
- MCP module guide: [../mcp/README.md](../mcp/README.md)
- Test module guide: [../tests/README.md](../tests/README.md)
- Deep architecture docs: [backend architecture](architecture/backend.md), [frontend architecture](architecture/frontend.md), [analyzer architecture](architecture/analyzer.md)

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
- `save_sections`
- `save_poi_target`

## Appendix: background on rendered sequence artifacts and ecosystem terms

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