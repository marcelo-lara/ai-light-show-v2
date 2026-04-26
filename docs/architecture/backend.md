# Backend — Architecture

The backend is a FastAPI + asyncio service that owns show state, cue rendering, and Art-Net output.

## Key modules

- `backend/main.py`: application lifecycle, startup loading, route wiring.
- `backend/mcp_server/*`: backend-mounted MCP tool registration and runtime adapters.
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
- Art-Net transmission is decoupled from canvas rendering and sends the current output universe at `30 FPS`.

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
7. Serve the mounted MCP endpoint from the same process so MCP clients share live backend state.
8. Websocket snapshot/event sends treat write failures as disconnect cleanup, so stale browser sockets are removed instead of surfacing ASGI websocket errors.

### Playback and time sync

- Browser timeline is the authoritative clock and keeps backend timecode aligned on a short cadence while playback is running, while backend advances playback timecode continuously between sync updates.
- Song intents: `song.list|load`.
- Transport intents: `transport.play|pause|stop|jump_to_time|jump_to_section`.
- `jump_to_time` seeks and applies nearest precomputed frame.
- `jump_to_section` resolves `payload.section_index` against sections sorted by normalized start time (`start_s|start`), seeks to the section start time, and applies the nearest precomputed frame.
- `transport.stop` applies blackout by zeroing output universe before Art-Net update.

### Analysis placeholder state

- Frontend snapshots and patches include a top-level `analyzer` object.
- The payload is currently an inert placeholder used to preserve the Song Analysis layout while backend queue/runtime behavior is absent.
- `available` is `false`, `polling` is `false`, `playback_locked` is `false`, `task_types` and `items` are empty, and `summary` is zeroed.

### Section metadata normalization

- Backend accepts section records with either `start`, `end`, `label` keys or normalized keys (`start_s`, `end_s`, `name`).
- Canonical persisted `sections.json` is a top-level list of section objects; authored `description` and `hints` stay on those same section rows.
- Song payload serialization always emits `{name, start_s, end_s}` for frontend state.
- Playback section name resolution and song length inference use normalized section fields (`start_s|start`, `end_s|end`, `name|label`).

### Beat metadata normalization

- Canonical beat rows are exposed through `state.song.beats` and MCP metadata tools.
- Backend resolves the active beats file from `info.json` metadata keys such as `beats_file`, `outputs.beats`, `artifacts.beats`, or `generated_from.timing_grid`.
- Beat rows always serialize `time`, `bar`, `beat`, optional `bass`/`chord`, and `type`.
- `type` is `downbeat` when `beat == 1`, otherwise `beat`.

### Editing

- `fixture.set_values` writes mapped channels to Art-Net and updates fixture `current_values`; for `kind="rgb"` meta-channels, payload must use `values.rgb` as `#RRGGBB` (or mapped color name), and backend converts it to RGB channel writes.
- `fixture.set_arm` updates per-fixture arm state cache used in frontend payload.
- `song.list` emits an event with the available backend song names and does not broadcast state.
- `song.load` validates `payload.filename`, loads the selected song, stops playback ticker activity, disables continuous Art-Net send, reapplies the loaded output universe, and broadcasts the updated song/cue/playback state.
- When `info.json` is missing for the selected song, `song.load` falls back to empty metadata (`bpm=0`, `duration=0`, empty beats path, empty artifacts) so the backend can still load the song and emit a valid snapshot.
- Song-scoped human hints are loaded from `data/reference/{song}/human/human_hints.json` through the shared `/data` root. Backend exposes them under `state.song.analysis.human_hints[]` with companion `state.song.analysis.human_hints_status`, and `song.hints.create|update|delete` persist edits immediately.
- Cue edits are handled by websocket intents: `cue.add`, `cue.update`, `cue.delete`, `cue.clear`, `cue.clear_all`, `cue.reload`, and `cue.apply_helper`.
- The mounted MCP server exposes parallel editing operations for LLM clients: full cue sheet reads, cue-window reads, cue add/update/delete, cue-window replace, and full-sheet replace.
- The mounted MCP server exposes canvas inspection operations for LLM clients: `render_dmx_canvas` refreshes the derived canvas and rewrites `backend/cues/{song}.dmx.log`, and `read_fixture_output_window` returns sampled fixture-channel output from that rendered canvas.
- The mounted MCP server exposes read helpers for assistant grounding beyond cue CRUD: transport cursor lookup, loudness summaries, fixture lists, chaser lists, beat windows, exact bar/beat lookup, chord windows, section windows with resolved musical positions, and section-analysis summaries for metadata drafting.
- `cue.clear` removes cue entries by time range (`from_time`, optional `to_time`) and persists the updated cue sheet.
- `cue.clear_all` removes every cue entry from the current song and persists the empty cue sheet.
- `cue.reload` re-reads the current song cue file from disk, validates the mixed cue rows against the active fixture and chaser inventory, and rebuilds the pre-rendered DMX canvas.
- LLM chat is backend-owned through `services/assistant/*`: prompt profiles are loaded there, requests are relayed to the agent gateway, and assistant websocket events are targeted to the requesting client instead of globally broadcast.
- The assistant service keeps recent per-client user and assistant turns for the lifetime of the websocket session and includes them in later `llm.send_prompt` requests.
- The default assistant prompt profile prefers grounded timing answers in `bar.beat (seconds)` form when both values are available, and it avoids repeating the loaded song name unless the user explicitly asks for it.
- Assistant websocket intents are `llm.send_prompt`, `llm.cancel`, `llm.confirm_action`, and `llm.reject_action`.
- Assistant event messages are `llm_status`, `llm_delta`, `llm_done`, `llm_action_proposed`, `llm_action_applied`, `llm_action_rejected`, `llm_cancelled`, and `llm_error`.
- Confirmed assistant mutations are terminal for the current turn: backend applies the action, emits `llm_action_applied`, then emits a backend-generated completion summary and `llm_done` without asking the gateway for another follow-up turn.
- Cue helper definitions are exposed in `state.cue_helpers` and helper execution is backend-owned.
- `cue.apply_helper` accepts `payload.helper_id` plus optional `payload.params`. Backend validates the helper id, uses helper-owned parameter defaults and validation, then upserts the generated cue rows.
- `cue_helper_apply_failed` carries `missing_artifacts` when helper execution detects absent artifact files, allowing frontend error UI to report the exact artifact names and resolved paths.
- `state.cue_helpers` includes a parameter schema for each helper so the frontend can render helper-specific controls without hardcoded forms.
- Cue persistence de-duplicates matching effect identities (`fixture_id` + `effect`) and matching chaser identities (`chaser_id`) within `100ms`, keeping the latest write even when the duplicate arrives through assistant-confirmed MCP-backed edits.
- Chaser definitions are loaded from `backend/chasers/*.json` and exposed in `state.chasers`.
- Chaser intents are `chaser.apply`, `chaser.preview`, `chaser.stop_preview`, `chaser.start`, `chaser.stop`, and `chaser.list`.
- Chaser effect fields `beat` and `duration` are beat-based; conversion uses `beatToTimeMs(beat_count, bpm)`.
- Persisted chaser cue rows store `chaser_id` and `data.repetitions`; they are not flattened on save.
- Render and preview paths expand chaser cue rows using song BPM plus beat offsets from the chaser definition.
- Persisted chaser rows use `created_by` set to `chaser:{id}`.
- `chaser.preview` renders temporary Art-Net output and does not persist cue data.
- `full` means full-on output only. It is not used as a blackout shortcut.
- `blackout` is the dedicated immediate-off effect for fixture blackout intentions.
- `fade_out` is the dedicated fade-to-zero effect. When no start value is provided it fades from full light, and when a start value is provided it fades from that level instead. Fractional `0..1` start values are normalized to `0..255` DMX bytes before rendering.
- Parcan `flash` accepts optional `color` and `brightness` data. `brightness` accepts either normalized `0..1` values or DMX-scaled bytes and defines the flash start level before the fade.
- Moving-head `strobe` is generated by the dimmer channel only. Dedicated fixture `strobe` and `shutter` channels stay at their existing values during the effect.
- Moving-head `orbit` is a POI-centered motion effect with physical travel compensation. The renderer starts it early with dark pre-roll from the last known pan/tilt position to `start_POI`, using template `physical_movement` timing plus `100 ms` safety and `100 ms` settle time. The visible motion rotates around `subject_POI` for the requested `orbits`, shrinks the orbit radius to zero by cue end, and limits per-frame pan/tilt changes to the fixture's maximum physical travel. `easing` controls the spiral collapse profile: `late_focus` keeps the circle wide longer, `balanced` is neutral, `linear` is constant, and `early_focus` tightens quickly.
- Moving-head `circle` uses the POI reference cube to estimate a large circular path around `target_poi`/`target_POI`. `radius` is normalized room-space distance from the target location, and signed `orbits` reverse the circle direction without changing the target.
- `sweep` moving-head cues compute a dark pre-roll from the last known pan/tilt position to `start_POI`, using each fixture template's `physical_movement.pan_full_travel_seconds` and `physical_movement.tilt_full_travel_seconds` values plus an extra `100 ms` safety pre-roll. The renderer starts the cue early by that offset, moves the head to `start_POI`, holds there dark for `100 ms`, then uses per-leg cubic easing: ease-out into `subject_POI`, ease-in away from it, and a mirrored dimmer envelope controlled by `dimmer_easing` (`0` starts fading immediately at visible start, `1` delays until almost at the subject). Visible pan/tilt motion is clamped per frame to the fixture's maximum physical travel, so the actual beam can lag the ideal path on slower fixtures. When the fixture is on the subject POI, output intensity reaches `max_dim`.

### Preview

- `fixture.preview_effect` validates fixture/effect/duration, renders temporary canvas, streams it to output at 60 FPS via Art-Net, and emits:
- `fixture.preview_effect` validates fixture/effect/duration, renders temporary canvas, updates preview frames at 60 FPS, and the Art-Net service transmits the current output universe at 30 FPS. It emits:
  - `preview_started` on success.
  - `preview_rejected` on failure.
- `chaser.preview` validates chaser input, renders temporary chaser canvas, updates preview frames at 60 FPS, and the Art-Net service transmits the current output universe at 30 FPS. It emits:
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

## MCP surface

- Mounted endpoint: `/mcp`
- Transport: Streamable HTTP
- Runtime ownership: the mounted MCP app uses the same `WebSocketManager`, `SongService`, and `StateManager` instances initialized in `backend/main.py`.

Current mounted MCP tools:
- `songs_list`, `songs_get_details`, `songs_load`
- `fixtures_list`, `fixtures_get`, `chasers_list`, `list_effects`
- `cues_get_sheet`, `cues_get_window`, `cues_add_entry`, `cues_update_entry`, `cues_delete_entry`, `cues_replace_sheet`, `cues_replace_window`
- `render_dmx_canvas`, `read_fixture_output_window`
- `metadata_get_overview`, `metadata_get_sections`, `metadata_get_song_analysis`, `metadata_get_section_analysis`, `metadata_find_section`, `metadata_get_beats`, `metadata_get_bar_beats`, `metadata_find_bar_beat`, `metadata_get_chords`, `metadata_find_chord`, `metadata_get_loudness`
- `transport_get_cursor`

Mutation tools schedule websocket patch broadcasts after state changes so browser clients remain synchronized with MCP-originated edits.

`list_effects` exposes the canonical effect registry metadata, including assistant-facing descriptions, controlled tags, and effect data schemas.

Serialized fixture payloads expose `supported_effects` as rich effect objects with `id`, `name`, `description`, `tags`, and `schema` rather than effect ids only.

Frontend consumers should treat each `supported_effects[]` entry as a metadata object. `id` is the stable effect identifier for intent payloads and parameter-schema lookup, and `name` is the display label.

`transport_get_cursor` returns the current timecode, nearest and next beat positions, the active `section_name` when the cursor is inside a labeled section, and `next_section_name` when the cursor is before the next section boundary.
`metadata_get_song_analysis` returns the backend-normalized song-analysis contract used by draft generation. It keeps artifact-file specifics behind one backend boundary and exposes section timing plus per-stem accents, dips, low windows, and dominant-part summaries.
`metadata_get_section_analysis` summarizes each section with mix loudness stats, harmonic spans/change points, and stem-supported evidence from `mix`, `bass`, `drums`, and `vocals` so the assistant can draft grounded descriptions and hints.

`cue.apply_helper` includes helper id `song_draft`, which generates a backend-owned draft cue sheet from song timing/features and the active rig's supported effects and POI coverage.

Backend resolves metadata from `/app/meta` in Docker. For local development and tests it prefers `data/output` and falls back to `backend/meta` only when no local metadata tree is present.

Backend resolves song audio from `/app/songs` in Docker. For local development and tests it prefers `data/songs`.

Song snapshot payload includes optional analysis artifacts under `song.analysis`:
- `plots[]`: backend-served SVG plot descriptors.
- `chords[]`: chord-change timeline entries when metadata exists.
- `events[]`: song-event timeline entries read from `outputs.song_event_timeline`, sorted by `start_time`, with timing, section, confidence/intensity, provenance, summary, creator, evidence summary, and lighting hint fields. `evidence_ref` stays backend-side.
- `patterns[]`: chord-pattern mining entries read from `artifacts.pattern_mining`, sorted by descending normalized occurrence count, with `id`, `label`, `bar_count`, `sequence`, and normalized `occurrences[]` timing/bar spans.

Static file serving for frontend assets consumed from snapshots:
- `/songs/*`: song audio files.
- `/meta/*`: metadata artifacts (SVG/JSON).

Patch behavior:
- Current diff granularity is top-level key replacement only.
- While playback is `playing`, backend suppresses `fixtures` patch updates to reduce frontend churn.

## Art-Net output

See `backend/services/artnet.py`.

- Sends ArtDMX packets to configured target.
- Sends the current output universe at `30 FPS`.
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
  tests/test_song_analysis_payload_events.py \
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
| Song metadata structure and loading paths | `backend/models/song/*` | validation command above + `tests/test_song_sections_payload_schema.py` + `tests/test_song_analysis_payload_chords.py` + `tests/test_song_analysis_payload_events.py` |
| Song metadata length inference or metadata path resolution | `backend/store/state_manager/core/metadata.py`, `backend/store/services/song_metadata_loader.py` | validation command above + `tests/test_song_sections_payload_schema.py` + `tests/test_song_analysis_payload_chords.py` + `tests/test_song_analysis_payload_events.py` |
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
