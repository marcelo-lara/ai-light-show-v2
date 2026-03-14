# Backend — Architecture

The backend is a FastAPI + asyncio service that owns show state, cue rendering, and Art-Net output.

## Key modules

- `backend/main.py`: application lifecycle, startup loading, route wiring.
- `backend/api/websocket_manager/endpoint.py`: websocket accept/read loop.
- `backend/api/websocket_manager/messaging.py`: inbound message handling and event/snapshot sends.
- `backend/api/websocket_manager/broadcasting.py`: throttled patch broadcasts.
- `backend/api/intents/*`: intent registry + action handlers (`transport`, `fixture`, `cue`, `poi`, `llm` domains).
- `backend/store/state.py`: compatibility export for `StateManager`, `FPS`, and `MAX_SONG_SECONDS`.
- `backend/store/state_manager/manager.py`: `StateManager` mixin composition root.
- `backend/store/state_manager/core/*`: bootstrap, fixture/POI store operations, metadata helpers, render wrappers.
- `backend/store/state_manager/song/*`: song load + cue/section persistence operations.
- `backend/store/state_manager/playback/*`: transport, preview lifecycle, channel edits, frame application.
- `backend/store/services/*`: collaborator services for fixture/template loading, metadata resolution, section persistence, and canvas rendering/debug output.
- `backend/store/dmx_canvas.py`: memory-efficient DMX frame buffer.
- `backend/store/pois.py`: POI persistence and runtime lookup.
- `backend/services/artnet.py`: Art-Net sender loop.

Compatibility exports:
- `backend/api/websocket.py` re-exports websocket manager entrypoints.
- `backend/api/ws_handlers.py` and `backend/api/ws_state_builder.py` re-export helpers.
- `backend/store/state.py` re-exports state-manager public symbols.

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
- `jump_to_section` resolves `payload.section_index` against sections sorted by normalized start time (`start_s|start`), seeks to the section start time, and applies the nearest precomputed frame.

### Section metadata normalization

- Backend accepts section records with either analyzer keys (`start`, `end`, `label`) or normalized keys (`start_s`, `end_s`, `name`).
- Song payload serialization always emits `{name, start_s, end_s}` for frontend state.
- Playback section name resolution and song length inference use normalized section fields (`start_s|start`, `end_s|end`, `name|label`).

### Editing

- `fixture.set_values` writes mapped channels to Art-Net and updates fixture `current_values`; for `kind="rgb"` meta-channels, payload must use `values.rgb` as `#RRGGBB` (or mapped color name), and backend converts it to RGB channel writes.
- `fixture.set_arm` updates per-fixture arm state cache used in frontend payload.

### Preview

- `fixture.preview_effect` validates fixture/effect/duration, renders temporary canvas, streams it to output at 60 FPS via Art-Net, and emits:
  - `preview_started` on success.
  - `preview_rejected` on failure.
- Preview runs to completion; final effect values persist to `editor_universe` and `output_universe`.
- `fixture.stop_preview` currently emits warning event and is not implemented.
- Preview is not written to cues/files, but final values remain active until overwritten.

## WebSocket protocol

See `docs/architecture/backend_llm_reference.md` for exact payloads and event catalog.

Message types:
- Client → backend: `hello`, `intent`.
- Backend → client: `snapshot`, `patch`, `event`.

Song snapshot payload includes optional analysis artifacts under `song.analysis`:
- `plots[]`: backend-served SVG plot descriptors.
- `chords[]`: chord-change timeline entries when metadata exists.

Static file serving for frontend assets consumed from snapshots:
- `/songs/*`: song audio files.
- `/meta/*`: analyzer metadata artifacts (SVG/JSON).

Patch behavior:
- Current diff granularity is top-level key replacement only.

## Art-Net output

See `backend/services/artnet.py`.

- Sends ArtDMX packets to configured target.
- Loop runs continuously.
- If `continuous_send` is disabled, identical frames are suppressed.

## Validation Commands

Use the `ai-light` environment for backend validation:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q \
  tests/test_set_values_regression.py \
  tests/test_preview_lifecycle_regression.py \
  tests/test_metadata_sections_regression.py \
  tests/test_dmx_canvas_render_new.py \
  tests/test_fixture_loading_new.py \
  tests/test_payload.py
```

## LLM Change Matrix

| If you change... | Edit here first | Then run... |
| --- | --- | --- |
| State bootstrap fields or shared state flags | `backend/store/state_manager/core/bootstrap.py` | validation command above |
| Fixture load/save, arm defaults, POI fixture target persistence | `backend/store/state_manager/core/fixture_store.py`, `backend/store/state_manager/core/fixture_effects.py` | validation command above |
| Song metadata structure and loading paths | `backend/models/song/*` | validation command above + `tests/test_metadata_sections_regression.py` |
| Song metadata length inference or metadata path resolution | `backend/store/state_manager/core/metadata.py`, `backend/store/services/song_metadata_loader.py` | validation command above + `tests/test_metadata_sections_regression.py` |
| Cue-sheet-to-canvas render wiring or preview render wiring | `backend/store/state_manager/core/render.py`, `backend/store/services/canvas_rendering.py` | validation command above |
| Song load, cue persistence, section persistence | `backend/store/state_manager/song/loading.py`, `backend/store/state_manager/song/cues.py`, `backend/store/state_manager/song/sections.py` | validation command above |
| Playback transport or timecode/frame application | `backend/store/state_manager/playback/transport.py` | validation command above |
| Preview start/stop/runner behavior | `backend/store/state_manager/playback/preview_start.py`, `backend/store/state_manager/playback/preview_control.py`, `backend/store/state_manager/playback/preview_runner.py` | validation command above + `tests/test_preview_lifecycle_regression.py` |
| Fixture live value write behavior | `backend/api/intents/fixture/actions/set_values.py`, `backend/store/state_manager/playback/channels.py` | validation command above + `tests/test_set_values_regression.py` |
| Snapshot or patch payload schema | `backend/api/state/*`, `backend/api/websocket_manager/broadcasting.py` | `tests/test_payload.py` |
| Websocket intent/message behavior | `backend/api/websocket_manager/*`, `backend/api/intents/*` | `PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q tests/test_ws_poi_e2e.py` |
| Import path or module composition for state manager | `backend/store/state.py`, `backend/store/state_manager/manager.py` | validation command above |
