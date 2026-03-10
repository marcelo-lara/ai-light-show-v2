# Backend — Architecture

The backend is a FastAPI + asyncio service that owns show state, cue rendering, and Art-Net output.

## Key modules

- `backend/main.py`: application lifecycle, startup loading, route wiring.
- `backend/api/websocket_manager/endpoint.py`: websocket accept/read loop.
- `backend/api/websocket_manager/messaging.py`: inbound message handling and event/snapshot sends.
- `backend/api/websocket_manager/broadcasting.py`: throttled patch broadcasts.
- `backend/api/intents/*`: intent registry + action handlers.
- `backend/store/state.py`: `StateManager` (authoritative runtime state + orchestration).
- `backend/store/services/*`: collaborator services for fixture/template loading, metadata resolution, section persistence, and canvas rendering/debug output.
- `backend/store/dmx_canvas.py`: memory-efficient DMX frame buffer.
- `backend/store/pois.py`: POI persistence and runtime lookup.
- `backend/services/artnet.py`: Art-Net sender loop.

Compatibility exports:
- `backend/api/websocket.py` re-exports websocket manager entrypoints.
- `backend/api/ws_handlers.py` and `backend/api/ws_state_builder.py` re-export helpers.

## Data model

### Cue sheet (effect-based)

- File: `backend/cues/{song}.cue.json`.
- Entries are effect instructions, not DMX snapshots.
- Renderer expands entries into a full timeline canvas at `60 FPS`.

### Dual universe model

`StateManager` keeps two universes and delegates parsing/render/persistence boundaries to `store/services/*`:
- `editor_universe`: authoring/edit baseline.
- `output_universe`: universe currently sent by Art-Net.

Behavior:
- Playing: output follows rendered canvas frame for current timecode.
- Paused: output defaults to editor universe.
- Preview active (paused): preview canvas temporarily drives output.

## Runtime behavior

### Startup

1. Load fixture instances and templates.
2. Load POIs.
3. Apply arm defaults.
4. Start Art-Net send loop.
5. Load default song and pre-render canvas.
6. Sync initial output universe.

### Playback and time sync

- Browser timeline is authoritative.
- Transport intents: `transport.play|pause|stop|jump_to_time|jump_to_section`.
- `jump_to_time` seeks and applies nearest precomputed frame.
- `jump_to_section` currently emits warning event and is not implemented.

### Editing

- `fixture.set_values` writes mapped channels to Art-Net and updates fixture `current_values`; for `kind="rgb"` meta-channels, payload must use `values.rgb` as `#RRGGBB` (or mapped color name), and backend converts it to RGB channel writes.
- `fixture.set_arm` updates per-fixture arm state cache used in frontend payload.

### Preview

- `fixture.preview_effect` validates fixture/effect/duration, renders temporary canvas, streams it to output, and emits:
  - `preview_started` on success.
  - `preview_rejected` on failure.
- `fixture.stop_preview` currently emits warning event and is not implemented.
- Preview is non-persistent (not written to cues/files).

## WebSocket protocol

See `docs/architecture/backend_llm_reference.md` for exact payloads and event catalog.

Message types:
- Client → backend: `hello`, `intent`.
- Backend → client: `snapshot`, `patch`, `event`.

Patch behavior:
- Current diff granularity is top-level key replacement only.

## Art-Net output

See `backend/services/artnet.py`.

- Sends ArtDMX packets to configured target.
- Loop runs continuously.
- If `continuous_send` is disabled, identical frames are suppressed.
