# Backend — Architecture

The backend is a FastAPI + asyncio service responsible for:

- Maintaining show state (fixtures, cues, playback state).
- Rendering a precomputed 60 FPS DMX canvas for the loaded song.
- Selecting the correct frame for the frontend-provided timecode/seek.
- Emitting Art-Net DMX frames continuously.
- Providing the *only* control plane via WebSocket at `/ws`.

## Key modules

- `backend/main.py`: app lifecycle, service wiring, startup fixture loading and song load.
- `backend/api/websocket.py`: message protocol handler.
- `backend/store/state.py`: StateManager (fixtures, cue sheet, universes, canvas, playback).
- `backend/store/dmx_canvas.py`: DMX canvas memory layout.
- `backend/services/artnet.py`: Art-Net UDP sender.
- `backend/services/song_service.py`: song discovery + metadata helpers.

## Data model

### Cue sheet (effect-based)

- Location: `backend/cues/{song}.cue.json`
- Entries are effect instructions (not snapshots).
- The current authoring UI records `set_channels` effects per fixture.

### Two universes: editor vs output

`StateManager` holds:

- `editor_universe`: live slider edits (authoring).
- `output_universe`: what Art-Net emits.

Routing policy:

- Paused: deltas update output (manual edit mode).
- Playing: output follows the DMX canvas; manual delta edits are rejected.
- Preview (paused only): temporary preview canvas overrides output for its duration, then output returns to editor universe.

## Runtime behavior

### Startup

1. Load fixtures from `backend/fixtures/fixtures.json`.
2. Apply fixture `arm` defaults.
3. Start the Art-Net sender loop (~60 FPS).
4. Load a default song (first available or a preferred name).
5. Build DMX canvas and sync frame 0 to output.

### Playback (frontend-authoritative time)

- `playback`: toggles backend play state.
- `timecode`: while playing, selects nearest canvas frame.
- `seek`: selects frame immediately; when paused also sends a snapshot (`dmx_frame`) so UI sliders match the preview.
- If playback starts while a preview is active, preview is cancelled immediately.

### Effect preview

- Message: `preview_effect` with fixture/effect/duration/data payload.
- Backend validates fixture + supported effect + duration.
- Backend renders an in-memory temporary DMX canvas and streams frames to `output_universe`.
- Preview is non-persistent (not written to cue sheet or disk).
- Backend broadcasts `preview_status` and global `status` transitions.

## WebSocket protocol

See `docs/architecture.md` for the canonical message list.

## Art-Net output

See `backend/services/artnet.py`.

- Sends ArtDMX packets to the configured node.
- Continues sending at ~60 FPS regardless of message traffic.
