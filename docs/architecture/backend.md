# Backend — Architecture

The backend is a FastAPI + asyncio service that owns show state, cue rendering, and Art-Net output.

## Key modules

- `backend/main.py`: application lifecycle, startup loading, route wiring.
- `backend/api/websocket_manager/endpoint.py`: websocket accept/read loop.
- `backend/api/websocket_manager/messaging.py`: inbound message handling and event/snapshot sends.
- `backend/api/websocket_manager/broadcasting.py`: throttled patch broadcasts.
- `backend/api/intents/*`: intent registry + action handlers (`song`, `transport`, `fixture`, `cue`, `chaser`, `poi`, `llm` domains).
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

### Cue sheet (mixed effect + chaser)

- File: `backend/cues/{song}.json`.
- Entries are cue instructions, not DMX snapshots.
- Effect rows store `time`, `fixture_id`, `effect`, `duration`, `data`, `name`, `created_by`.
- Chaser rows store `time`, `chaser_id`, `data`, `name`, `created_by`.
- Renderer expands chaser rows into effect rows at render time and builds the full timeline canvas at `60 FPS`.

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

- Browser timeline provides periodic alignment (for example every 10s), while backend advances playback timecode continuously during `playing`.
- Song intents: `song.list|load`.
- Transport intents: `transport.play|pause|stop|jump_to_time|jump_to_section`.
- `jump_to_time` seeks and applies nearest precomputed frame.
- `jump_to_section` resolves `payload.section_index` against sections sorted by normalized start time (`start_s|start`), seeks to the section start time, and applies the nearest precomputed frame.
- `transport.stop` applies blackout by zeroing output universe before Art-Net update.

### Section metadata normalization

- Backend accepts section records with either analyzer keys (`start`, `end`, `label`) or normalized keys (`start_s`, `end_s`, `name`).
- Song payload serialization always emits `{name, start_s, end_s}` for frontend state.
- Playback section name resolution and song length inference use normalized section fields (`start_s|start`, `end_s|end`, `name|label`).

### Editing

- `fixture.set_values` writes mapped channels to Art-Net and updates fixture `current_values`; for `kind="rgb"` meta-channels, payload must use `values.rgb` as `#RRGGBB` (or mapped color name), and backend converts it to RGB channel writes.
- `fixture.set_arm` updates per-fixture arm state cache used in frontend payload.
- `song.list` emits an event with the available backend song names and does not broadcast state.
- `song.load` validates `payload.filename`, loads the selected song, stops playback ticker activity, disables continuous Art-Net send, reapplies the loaded output universe, and broadcasts the updated song/cue/playback state.
- Cue edits are handled by websocket intents: `cue.add`, `cue.update`, `cue.delete`, `cue.clear`, and `cue.apply_helper`.
- `cue.clear` removes cue entries by time range (`from_time`, optional `to_time`) and persists the updated cue sheet.
- Cue helper definitions are exposed in `state.cue_helpers` and helper execution is backend-owned.
- Chaser definitions are loaded from `backend/fixtures/chasers.json` and exposed in `state.chasers`.
- Chaser intents are `chaser.apply`, `chaser.preview`, `chaser.stop_preview`, `chaser.start`, `chaser.stop`, and `chaser.list`.
- Chaser effect fields `beat` and `duration` are beat-based; conversion uses `beatToTimeMs(beat_count, bpm)`.
- Persisted chaser cue rows store `chaser_id` and `data.repetitions`; they are not flattened on save.
- Render and preview paths expand chaser cue rows using song BPM plus beat offsets from the chaser definition.
- Persisted chaser rows use `created_by` set to `chaser:{id}`.
- `chaser.preview` renders temporary Art-Net output and does not persist cue data.
- Moving-head `strobe` is generated by the dimmer channel only. Dedicated fixture `strobe` and `shutter` channels stay at their existing values during the effect.
- Moving-head `seek` is a POI-centered motion effect with physical travel compensation. The renderer starts it early with dark pre-roll from the last known pan/tilt position to `start_POI`, using template `physical_movement` timing plus `100 ms` safety and `100 ms` settle time. The visible motion rotates around `subject_POI` for the requested `orbits`, shrinks the orbit radius to zero by cue end, and limits per-frame pan/tilt changes to the fixture's maximum physical travel. `easing` controls the spiral collapse profile: `late_focus` keeps the circle wide longer, `balanced` is neutral, `linear` is constant, and `early_focus` tightens quickly.
- `sweep` moving-head cues compute a dark pre-roll from the last known pan/tilt position to `start_POI`, using each fixture template's `physical_movement.pan_full_travel_seconds` and `physical_movement.tilt_full_travel_seconds` values plus an extra `100 ms` safety pre-roll. The renderer starts the cue early by that offset, moves the head to `start_POI`, holds there dark for `100 ms`, then uses per-leg cubic easing: ease-out into `subject_POI`, ease-in away from it, and a mirrored dimmer envelope controlled by `dimmer_easing` (`0` starts fading immediately at visible start, `1` delays until almost at the subject). Visible pan/tilt motion is clamped per frame to the fixture's maximum physical travel, so the actual beam can lag the ideal path on slower fixtures. When the fixture is on the subject POI, output intensity reaches `max_dim`.

### Preview

- `fixture.preview_effect` validates fixture/effect/duration, renders temporary canvas, streams it to output at 60 FPS via Art-Net, and emits:
  - `preview_started` on success.
  - `preview_rejected` on failure.
- `chaser.preview` validates chaser input, renders temporary chaser canvas, streams output at 60 FPS via Art-Net, and emits:
  - `chaser_preview_started` on success.
  - `chaser_preview_rejected` on failure.
- `chaser.stop_preview` emits `chaser_preview_stopped` when active preview is cancelled.
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
- While playback is `playing`, backend suppresses `fixtures` patch updates to reduce frontend churn.

## Art-Net output

See `backend/services/artnet.py`.

- Sends ArtDMX packets to configured target.
- Loop runs continuously.
- If `continuous_send` is disabled, identical frames are suppressed.
- `DEBUG_MODE` enables DMX payload debug output to stdout and to a file if `DEBUG_FILE` is set.

## Validation Commands

Use the `ai-light` environment for backend validation:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q \
  tests/test_set_values_regression.py \
  tests/test_song_sections_payload_schema.py \
  tests/test_song_analysis_payload_chords.py \
  tests/test_jump_to_section_regression.py \
  tests/test_chaser_timing.py \
  tests/test_chaser_preview_lifecycle.py \
  tests/test_chaser_intents.py \
  tests/test_fixture_effect_preview_matrix.py \
  tests/test_fixture_effect_canvas_matrix.py \
  tests/test_dmx_canvas_render_new.py \
  tests/test_fixture_loading_new.py \
  tests/test_payload.py
```

For websocket/file-backed intent coverage, additionally run:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q \
  tests/test_ws_transport_jump_to_section_e2e.py \
  tests/test_ws_poi_e2e.py \
  tests/test_ws_cue_e2e.py \
  tests/test_ws_chaser_e2e.py \
  tests/test_ws_chaser_preview_e2e.py
```

## LLM Change Matrix

| If you change... | Edit here first | Then run... |
| --- | --- | --- |
| State bootstrap fields or shared state flags | `backend/store/state_manager/core/bootstrap.py` | validation command above |
| Fixture load/save, arm defaults, POI fixture target persistence | `backend/store/state_manager/core/fixture_store.py`, `backend/store/state_manager/core/fixture_effects.py` | validation command above |
| Song metadata structure and loading paths | `backend/models/song/*` | validation command above + `tests/test_song_sections_payload_schema.py` + `tests/test_song_analysis_payload_chords.py` |
| Song metadata length inference or metadata path resolution | `backend/store/state_manager/core/metadata.py`, `backend/store/services/song_metadata_loader.py` | validation command above + `tests/test_song_sections_payload_schema.py` + `tests/test_song_analysis_payload_chords.py` |
| Cue-sheet-to-canvas render wiring or preview render wiring | `backend/store/state_manager/core/render.py`, `backend/store/services/canvas_rendering.py` | validation command above |
| Fixture effect contracts or preview support | `backend/models/fixtures/**/*`, `backend/store/state_manager/core/fixture_effects.py`, `backend/store/state_manager/playback/preview_start.py` | validation command above + `tests/test_fixture_effect_preview_matrix.py` + `tests/test_fixture_effect_canvas_matrix.py` |
| Song load, cue persistence, section persistence | `backend/store/state_manager/song/loading.py`, `backend/store/state_manager/song/cues.py`, `backend/store/state_manager/song/sections.py` | validation command above |
| Song enumeration and load intents | `backend/api/intents/song/*`, `backend/services/song_service.py` | websocket/file-backed command above + `tests/test_song_intents.py` + `tests/test_ws_song_e2e.py` |
| Playback transport or timecode/frame application | `backend/store/state_manager/playback/transport.py` | validation command above + `tests/test_ws_transport_jump_to_section_e2e.py` |
| Chaser preview start/stop/runner behavior | `backend/store/state_manager/playback/preview_chaser.py` | validation command above + `tests/test_chaser_preview_lifecycle.py` |
| Fixture live value write behavior | `backend/api/intents/fixture/actions/set_values.py`, `backend/store/state_manager/playback/channels.py` | validation command above + `tests/test_set_values_regression.py` |
| Snapshot or patch payload schema | `backend/api/state/*`, `backend/api/websocket_manager/broadcasting.py` | `tests/test_payload.py` |
| Chaser timing, lifecycle, or handler behavior | `backend/store/state_manager/playback/*`, `backend/api/intents/chaser/*`, `backend/services/cue_helpers/*` | validation command above + websocket/file-backed command above |
| Cue intent or persistence behavior | `backend/api/intents/cue/*`, `backend/store/state_manager/song/cues.py` | validation command above + `tests/test_cue_add.py` + `tests/test_cue_clear.py` + `tests/test_cue_intents.py` + `tests/test_ws_cue_e2e.py` |
| Websocket intent/message behavior | `backend/api/websocket_manager/*`, `backend/api/intents/*` | websocket/file-backed command above |
| Import path or module composition for state manager | `backend/store/state.py`, `backend/store/state_manager/manager.py` | validation command above |
