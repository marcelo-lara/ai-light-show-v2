# Backend LLM Reference (Code-Accurate)

This document is an implementation-level reference for backend behavior in `backend/`.
Code is the source of truth.

## Runtime map

1. App bootstrap: `backend/main.py`
- Creates `StateManager`, `ArtNetService`, `SongService`, `WebSocketManager`.
- Creates and mounts the backend MCP server at `/mcp`.
- Loads POIs and fixtures.
- Arms fixtures and starts Art-Net send loop.
- Loads default song (`Yonaka - Seize the Power` if present, else first available).
- Mounts songs at `/songs` and exposes websocket endpoint at `/ws`.

2. WebSocket transport: `backend/api/websocket_manager/*`
- `endpoint.py`: accepts and reads websocket frames.
- `messaging.py`: parses incoming frames and dispatches intents.
- `broadcasting.py`: throttled patch broadcast (default `50ms`, slower cadence while playing).
- `manager.py`: shared state (`seq`, active connections, fixture arm cache).

3. Intent routing: `backend/api/intents/*`
- `apply_intent.py` dispatches by domain via `INTENT_HANDLERS`.
- Domains: `song`, `transport`, `fixture`, `cue`, `chaser`, `poi`, `llm`.

3a. MCP routing: `backend/mcp_server/*`
- `server.py` registers the mounted MCP tools.
- `runtime.py` binds the MCP server to the live backend `WebSocketManager` and `SongService` instances.
- Tool groups are split across `songs.py`, `fixtures.py`, `cues.py`, and `metadata.py`.

4. State authority: `backend/store/state.py`
- Holds fixtures, POIs, song/cue state, playback flags, preview lifecycle.
- Exposes `StateManager` via compatibility import from `backend/store/state_manager/*`.
- Uses subfolder modules:
  - `backend/store/state_manager/core/*`
  - `backend/store/state_manager/song/*`
  - `backend/store/state_manager/playback/*`
- Delegates fixture/template loading, song metadata resolution, section persistence, and canvas rendering helpers to `backend/store/services/*`.
- Pre-renders full song DMX canvas at `60 FPS`.
- Computes output frame from synchronized timecode.
- Advances playback timecode in backend via websocket-manager ticker while `playing`.

5. DMX output: `backend/services/artnet.py`
- Maintains active DMX universe.
- Sends Art-Net packets on loop.
- Sends only on change unless `continuous_send=True`.
- Prints DMX payload bytes to stdout and to a file if `DEBUG_FILE` is set when `DEBUG_MODE` is truthy.

## Behavior-critical modules and symbols

| Module | Key symbols | Runtime responsibility |
| --- | --- | --- |
| `backend/main.py` | `lifespan`, `websocket_route` | Startup/shutdown wiring and route exposure |
| `backend/mcp_server/server.py` | `create_backend_mcp` | Mounted MCP server composition |
| `backend/mcp_server/runtime.py` | `BackendMcpRuntime` | Holds runtime references for MCP tool handlers |
| `backend/mcp_server/song_data.py` | `build_song_details` | Shared song/analysis serialization for MCP tools |
| `backend/api/websocket_manager/manager.py` | `WebSocketManager` | Connection registry, sequencing, orchestration |
| `backend/api/websocket_manager/messaging.py` | `handle_message`, `send_snapshot`, `broadcast_event` | Protocol handling and message emission |
| `backend/api/websocket_manager/broadcasting.py` | `schedule_broadcast`, `broadcast_patch` | Throttled state-diff broadcasting |
| `backend/api/intents/apply_intent.py` | `apply_intent` | Intent dispatch and unknown-intent warning events |
| `backend/api/state/build_frontend_state.py` | `build_frontend_state` | Canonical snapshot/patch state payload |
| `backend/api/state/fixtures.py` | `build_fixtures_payload` | Fixture state serialization |
| `backend/models/song/*` | `Song`, `Meta`, `Beats`, `Sections` | Management models for Song metadata lazy loading and section handling |
| `backend/api/state/song_payload.py` | `build_song_payload` | Song metadata payload normalization |
| `backend/store/state.py` | `StateManager` (re-export) | Stable state manager import path for callers |
| `backend/store/state_manager/manager.py` | `StateManager` | Core show state composition root |
| `backend/store/state_manager/core/*` | core mixins | Bootstrap + fixture/POI + metadata + render helpers |
| `backend/store/state_manager/song/*` | song mixins | Song load and cue/section persistence |
| `backend/store/state_manager/playback/*` | playback mixins | Transport, preview lifecycle, and frame application |
| `backend/store/services/fixture_loader.py` | `load_fixtures_from_path` | Fixture/template loading and instantiation |
| `backend/store/services/song_metadata_loader.py` | `SongMetadataLoader` | Metadata candidate resolution + beats hydration |
| `backend/store/services/section_persistence.py` | `normalize_sections_input`, `persist_parts_to_meta` | Section validation and metadata persistence |
| `backend/store/services/canvas_rendering.py` | `render_cue_sheet_to_canvas`, `render_preview_canvas`, `dump_canvas_debug` | DMX canvas rendering + debug log dump |
| `backend/store/services/canvas_render_core.py` | `iter_cues_for_render`, `render_entry_into_universe` | Cue iteration and per-entry frame rendering helpers |
| `backend/store/services/canvas_debug.py` | `dump_canvas_debug` | Canvas debug file writer |
| `backend/services/cue_helpers/*` | `generate_downbeats_and_beats` | Backend-owned cue helper generation logic |
| `backend/store/pois.py` | `PoiDatabase` | POI CRUD + disk sync + runtime target lookup |
| `backend/store/dmx_canvas.py` | `DMXCanvas` | Packed DMX frame buffer |
| `backend/services/artnet.py` | `ArtNetService` | UDP Art-Net output |
| `backend/models/fixtures/moving_heads/moving_head.py` | `MovingHead.render_effect` | Moving-head cue/preview effect execution |
| `backend/models/fixtures/parcans/parcan.py` | `Parcan.render_effect` | Parcan cue/preview effect execution |

## WebSocket contract

### Inbound messages

1. `hello`
- Shape: `{"type":"hello", ...}`
- Behavior: backend sends full `snapshot`.

2. `intent`
- Shape: `{"type":"intent","req_id":string,"name":string,"payload":object}`
- Behavior: dispatches to intent handlers.
- If handler returns `True`, backend schedules a patch broadcast.
- If handler returns `False`, no patch broadcast (events may still be emitted).

### Outbound messages

1. `snapshot`
- Shape: `{"type":"snapshot","seq":number,"state":...}`
- Sent on connect and on `hello`.

2. `patch`
- Shape: `{"type":"patch","seq":number,"changes":[{"path":[key],"value":...}]}`
- Current diff granularity is top-level key replacement only (`system`, `playback`, `fixtures`, `song`, `pois`, `cues`, `cue_helpers`, `chasers`).

3. `event`
- Shape: `{"type":"event","level":"info|warning|error","message":string,"data"?:object}`

## MCP contract

- Endpoint: `/mcp`
- Transport: Streamable HTTP
- Configuration: mounted with stateless HTTP and JSON responses

### Current MCP tools

#### Songs

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `songs_list` | none | returns backend song ids from `SongService.list_songs()` |
| `songs_get_details` | `song?` | returns normalized song payload for the requested song or the currently loaded song |
| `songs_load` | `song` | loads the song into live backend state, stops playback ticker activity, disables continuous Art-Net send, reapplies output universe, schedules websocket broadcast |

#### Fixtures

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `fixtures_list` | none | returns serialized fixture payloads using current output universe values |
| `fixtures_get` | `fixture_id` | returns one serialized fixture payload |
| `chasers_list` | none | returns the currently loaded chaser definitions from `backend/fixtures/chasers.json` |

#### Cues

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `cues_get_sheet` | none | returns full cue sheet for current song |
| `cues_get_window` | `start_time`, `end_time` | returns entries whose `time` falls in the inclusive window |
| `cues_add_entry` | `entry` | adds one effect or chaser row, persists, re-renders canvas, schedules websocket broadcast |
| `cues_update_entry` | `index`, `patch` | updates one cue row by index, persists, schedules websocket broadcast |
| `cues_delete_entry` | `index` | deletes one cue row by index, persists, schedules websocket broadcast |
| `cues_replace_sheet` | `entries` | replaces the entire cue sheet after validation, persists, re-renders canvas, schedules websocket broadcast |

#### Metadata

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `metadata_get_overview` | `song?` | returns song length/BPM and counts for sections, beats, chords |
| `metadata_get_sections` | `song?` | returns normalized section rows |
| `metadata_get_beats` | `song?`, `start_time?`, `end_time?` | returns beat rows from backend metadata, optionally time-filtered |
| `metadata_get_chords` | `song?`, `start_time?`, `end_time?` | returns chord-change rows parsed from `beats.json`, optionally time-filtered |
| `metadata_get_loudness` | `song?`, `start_time?`, `end_time?`, `section?` | reads analyzer `essentia/loudness_envelope.json` and returns averaged window statistics |

#### Transport

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `transport_get_cursor` | none | returns current timecode plus nearest resolved `bar`, `beat`, and active `section_name` |

## Intent catalog (current implementation)

### Song intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `song.list` | none | emits `song_list` with backend-discoverable song names from `SongService.list_songs()` | `False` |
| `song.load` | `filename` | validates the song id, loads the selected song into `StateManager`, stops playback ticker activity, disables continuous Art-Net send, reapplies the loaded output universe, and emits `song_loaded` | `True` on success; else event `song_load_failed` and `False` |

### Transport intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `transport.play` | none | `set_playback_state(True)`, start backend playback ticker, enable continuous Art-Net send | `True` |
| `transport.pause` | none | `set_playback_state(False)`, stop backend playback ticker, disable continuous send | `True` |
| `transport.stop` | none | pause + stop ticker + seek `0` + blackout output universe + push Art-Net + disable continuous send | `True` |
| `transport.jump_to_time` | `time_ms` | seek to `max(0, time_ms/1000)` and push output universe | `True` on valid time, else event `invalid_time_ms` and `False` |
| `transport.jump_to_section` | `section_index` | sort sections by normalized start (`start_s|start`), seek to selected section start, then push output universe | `True` on valid index; else event `invalid_section_index`/`section_index_out_of_range`/`no_sections_available`/`song_not_loaded` and `False` |

### Fixture intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `fixture.set_arm` | `fixture_id`, `armed` | updates `manager.fixture_armed` only | `True` if `fixture_id` present, else event `fixture_id_required` and `False` |
| `fixture.set_values` | `fixture_id`, `values` | updates fixture `current_values` and applies mapped DMX channel writes to `ArtNetService` | `True` if any channel write applied |
| `fixture.preview_effect` | `fixture_id`, `effect_id`, `duration_ms`, `params` | validates and starts preview canvas playback; runs to completion and persists final values to `editor_universe` | `True` on success; else event `preview_rejected` and `False` |
| `fixture.stop_preview` | none | not implemented | event `stop_preview_not_implemented`, returns `False` |

Notes on `fixture.set_values`:
- `values` keys target meta-channel IDs from fixture template `meta_channels`.
- `u16` channels split into MSB/LSB writes.
- `enum` expects label and resolves via reverse mapping.
- `rgb` accepts either `#RRGGBB` or mapped color names and writes the RGB component channels declared in `meta_channels.<id>.channels`.
- Direct component channel payloads (`red`/`green`/`blue`) are ignored for fixtures that declare an `rgb` meta-channel.
- Current implementation does not hard-reject while playing.

### POI intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `poi.create` | POI object | creates POI in `pois.json` | `True` on success |
| `poi.update` | `id` + partial fields | updates POI by `id` | `True` if POI found/updated |
| `poi.delete` | `id` | deletes POI by `id` | `True` if POI existed |
| `poi.update_fixture_target` | `poi_id`, `fixture_id`, `pan`, `tilt` | clamps `pan/tilt` to `0..65535`, stores under POI fixtures map, sets `canvas_dirty` | `True` on success |

### Cue intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `cue.add` | effect row: `time`, `fixture_id`, `effect`, `duration`, `data`; chaser row: `time`, `chaser_id`, `data` | validates cue shape, fixture/effect or chaser id, adds entry to cue sheet, persists to disk, re-renders canvas | `True` on success; else event `cue_add_failed` and `False` |
| `cue.update` | `index`, `patch` | validates index/patch, updates cue entry, persists to disk | `True` on success; else event `cue_update_failed` and `False` |
| `cue.delete` | `index` | validates index, deletes cue entry, persists to disk | `True` on success; else event `cue_delete_failed` and `False` |
| `cue.clear` | `from_time?`, `to_time?` | validates numeric time range, removes entries in the requested range (`from_time` only clears from that time to end), persists, and re-renders when entries were removed | `True` on success; else event `cue_clear_failed` and `False` |
| `cue.apply_helper` | `helper_id` | validates helper, generates cue entries from song beats, upserts by `(time, fixture_id)`, persists, re-renders canvas, and tags `created_by` with helper id | `True` on success; else event `cue_helper_apply_failed` and `False` |

### Chaser intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `chaser.apply` | `chaser_id`, `start_time_ms?`, `repetitions?` | validates chaser id, persists one chaser cue row with `data.repetitions`, re-renders canvas, tags `created_by` as `chaser:{id}` | `True` on success; else event `chaser_apply_failed` and `False` |
| `chaser.preview` | `chaser_id`, `start_time_ms?`, `repetitions?` | expands chaser into temporary effect entries, renders non-persistent preview frames at 60 FPS, streams Art-Net output, does not write cues | `True` on success; else event `chaser_preview_rejected` and `False` |
| `chaser.stop_preview` | none | cancels active non-persistent chaser preview and restores editor output universe | emits `chaser_preview_stopped` when preview was active, otherwise `chaser_preview_stop_ignored`; returns `False` |
| `chaser.start` | `chaser_id`, `start_time_ms?`, `repetitions?` | applies chaser row and tracks runtime instance id in memory | `True` on success; else event `chaser_start_failed` and `False` |
| `chaser.stop` | `instance_id` | removes tracked runtime instance id from memory | emits `chaser_stopped`, returns `False` |
| `chaser.list` | none | emits `chaser_list` event with current chaser definitions | `False` |

### LLM intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `llm.send_prompt` | `prompt`, `assistant_id?` | starts a session-scoped assistant request, emits `llm_status`, `llm_delta`, `llm_done`, and optionally `llm_action_proposed` | `False` |
| `llm.cancel` | `request_id?` | cancels the active assistant request for the websocket session or the specified request | `False` |
| `llm.confirm_action` | `request_id`, `action_id` | applies a pending assistant action, emits `llm_action_applied`, then resumes model-authored response streaming | `False` |
| `llm.reject_action` | `request_id`, `action_id` | dismisses a pending assistant action and emits `llm_action_rejected` | `False` |

## Event message catalog

| Level | Message | `data` payload |
| --- | --- | --- |
| `error` | `invalid_json` | none |
| `warning` | `unsupported_message_type` | `{type: <received type>}` |
| `warning` | `unknown_intent` | `{name}` |
| `info` | `song_list` | `{songs:[...]}` |
| `info` | `song_loaded` | `{filename}` |
| `error` | `song_load_failed` | `{reason, filename?, songs?, error?}` |
| `error` | `invalid_time_ms` | none |
| `error` | `song_not_loaded` | none |
| `error` | `no_sections_available` | none |
| `error` | `invalid_section_index` | none |
| `error` | `section_index_out_of_range` | `{section_index, section_count}` |
| `error` | `fixture_id_required` | none |
| `warning` | `preview_rejected` | rejection object from `start_preview_effect` |
| `info` | `preview_started` | preview result object (`requestId`, `fixtureId`, `effect`, `duration`) |
| `warning` | `stop_preview_not_implemented` | none |
| `warning` | `chaser_preview_rejected` | rejection object from `start_preview_chaser` |
| `info` | `chaser_preview_started` | preview result object (`requestId`, `chaser_id`, `entries`) |
| `info` | `chaser_preview_stopped` | `{}` |
| `warning` | `chaser_preview_stop_ignored` | `{reason:"preview_not_active"}` |
| `error` | `prompt_required` | none |
| `info` | `llm_status` | `{domain:"llm", request_id, phase, label, assistant_id?}` |
| `info` | `llm_delta` | `{domain:"llm", request_id, delta, done:false}` |
| `info` | `llm_done` | `{domain:"llm", request_id, finish_reason, done:true}` |
| `info` | `llm_action_proposed` | `{domain:"llm", request_id, action_id, title, summary, tool_name, arguments, requires_confirmation:true}` |
| `info` | `llm_action_applied` | `{domain:"llm", request_id, action_id, tool_name}` |
| `info` | `llm_action_rejected` | `{domain:"llm", request_id, action_id}` |
| `info` | `llm_cancelled` | `{domain:"llm", request_id}` |
| `error` | `llm_error` | `{domain:"llm", request_id, code, detail, retryable}` |
| `error` | `cue_add_failed` | `{reason, fixture_id?, effect?, supported?}` |
| `info` | `cue_added` | `{ok, entry}` |
| `error` | `cue_update_failed` | `{reason}` |
| `info` | `cue_updated` | `{ok, entry}` |
| `error` | `cue_delete_failed` | `{reason}` |
| `info` | `cue_deleted` | `{ok, entry}` |
| `error` | `cue_helper_apply_failed` | `{reason, helper_id?}` |
| `info` | `cue_helper_applied` | `{helper_id, generated, replaced, skipped}` |
| `error` | `chaser_apply_failed` | `{reason, chaser_id?}` |
| `info` | `chaser_applied` | `{chaser_id, entry}` |
| `error` | `chaser_start_failed` | `{reason, chaser_id?}` |
| `info` | `chaser_started` | `{instance_id, chaser_id, ...}` |
| `error` | `chaser_stop_failed` | `{reason, instance_id?}` |
| `info` | `chaser_stopped` | `{instance_id}` |
| `info` | `chaser_list` | `{chasers:[...]}` |

MCP tools return structured envelopes instead of websocket events:
- success: `{ "ok": true, "data": { ... } }`
- error: `{ "ok": false, "error": { "code", "message", "details?" } }`

## Snapshot state schema

Top-level state object:

```json
{
  "system": {
    "show_state": "running|idle",
    "edit_lock": true
  },
  "playback": {
    "state": "playing|paused|stopped",
    "time_ms": 0,
    "bpm": 128.0,
    "section_name": "verse"
  },
  "fixtures": {
    "fixture_id": {
      "id": "fixture_id",
      "name": "Fixture Name",
      "type": "moving_head|parcan|...",
      "armed": true,
      "values": {},
      "capabilities": {"pan_tilt": true, "rgb": false},
      "meta_channels": {},
      "mappings": {},
      "supported_effects": ["flash", "strobe", "full"]
    }
  },
  "song": {
    "filename": "Song",
    "audio_url": "/songs/Song.mp3",
    "length_s": 180,
    "bpm": 120,
    "sections": [{"name": "intro", "start_s": 0.0, "end_s": 12.5}],
    "beats": [{"time": 0.5, "bar": 0, "beat": 2}, {"time": 1.0, "bar": 0, "beat": 3}],
    "analysis": {
      "plots": [{"id": "rhythm", "title": "Rhythm", "svg_url": "/meta/Song/essentia/rhythm.svg"}],
      "chords": [{"time_s": 12.0, "label": "Fm", "bar": 8, "beat": 1}]
    }
  },
  "pois": [],
  "cues": [
    {"time": 0.0, "fixture_id": "parcan_l", "effect": "flash", "duration": 0.5, "data": {}, "name": null, "created_by": "user"},
    {"time": 1.36, "chaser_id": "blue_parcan_chase", "data": {"repetitions": 1}, "name": null, "created_by": "user"}
  ],
  "cue_helpers": [
    {"id": "downbeats_and_beats", "label": "DownBeats and Beats", "description": "...", "mode": "full_song"}
  ],
  "chasers": [
    {
      "id": "downbeats_and_beats",
      "name": "Downbeat plus two beats",
      "description": "A simple chaser pattern",
      "effects": [
        {"beat": 0.0, "fixture_id": "parcan_pl", "effect": "flash", "duration": 1.5, "data": {}}
      ]
    }
  ]
}
```

Field notes:
- `system.edit_lock` is `True` when playback is active.
- `playback.state` derives from `isPlaying` plus `timecode` (`stopped` only at ~0).
- `song` is `null` when no song is loaded.
- `song.analysis` is optional and is present only when analysis artifacts exist for the loaded song.
- For RGB fixtures, `fixtures.<id>.values.rgb` is emitted as canonical uppercase `#RRGGBB`.
- `fixtures.<id>.supported_effects` lists valid effect names for `fixture.preview_effect` and `cue.add` intents.
- Input section records may be `start/end/label` or `start_s/end_s/name`; emitted `song.sections[]` entries are normalized to `{name,start_s,end_s}`.
- `cues` contains the cue sheet entries for the loaded song; empty array if no cue sheet. Each cue entry includes `created_by`.
- `cue_helpers` lists backend-declared helper definitions for frontend helper execution UI.
- `chasers` lists chaser definitions loaded from `backend/fixtures/chasers.json`.
- Chaser effect fields `beat` and `duration` are in beats and converted using `beatToTimeMs(beat_count, bpm)` when generating cues.

Patch behavior during playback:
- While `playback.state` is `playing`, websocket patch generation suppresses `fixtures` updates.

## Effect data contracts

### Moving head effects

| Effect | Required/expected `data` keys | Behavior |
| --- | --- | --- |
| `move_to` | pan/tilt targets (`pan`/`tilt` u16 or axis byte variants/preset) | interpolates pan/tilt across cue duration |
| `move_to_poi` | `target_POI` (also accepts `poi` or `POI`) | interpolates toward POI target for this fixture |
| `seek` | required `subject_POI`, `start_POI`; optional `orbits`, `easing` | schedules dark pre-roll to `start_POI` from the last known pan/tilt using fixture-template `physical_movement` timing, then circles around `subject_POI` and spirals into the subject by cue end while limiting per-frame pan/tilt changes to the fixture's maximum physical travel; recommended easing is `late_focus`, with `balanced`, `linear`, and `early_focus` also supported |
| `strobe` | optional `rate` (Hz) | toggles dimmer only; dedicated fixture `strobe`/`shutter` channels are left unchanged |
| `full` | none | instant full-on dimmer (+ shutter if available) |
| `flash` | none | fades dimmer from 255 to 0 over duration |
| `fade_in` | optional `dim`/`dimmer`/`intensity` target | interpolates intensity from current value to target and opens shutter when present |
| `sweep` | required `subject_POI`, `start_POI`; optional `end_POI`, `duration`, `easing`, `dimmer_easing`, `arc_strength`, `max_dim` | computes a dark pre-roll from the last known pan/tilt to `start_POI` using fixture-template `physical_movement` pan/tilt full-range timing plus an extra `100 ms` safety pre-roll, holds at `start_POI` for `100 ms`, then runs a two-leg arc sweep with cubic ease-out into the subject, cubic ease-in away from it, mirrored dimmer timing, and per-frame pan/tilt clamping to the fixture's maximum physical travel; `max_dim` is reached when the actual pan/tilt land on the subject POI |

### Parcan effects

| Effect | Required/expected `data` keys | Behavior |
| --- | --- | --- |
| `flash` | optional `channels` list | fades selected channels (default RGB) |
| `strobe` | optional `rate` or `speed` | toggles RGB between cached "on" color and off |
| `fade_in` | any of `red`, `green`, `blue` | interpolates from current RGB to targets |
| `full` | optional `red`, `green`, `blue` | instant RGB set (default white) |

## Notes on legacy wrappers

- `backend/api/websocket.py` re-exports websocket manager entrypoints.
- `backend/api/ws_handlers.py` and `backend/api/ws_state_builder.py` are compatibility exports.
- Domain `router.py` files exist but main dispatch uses `INTENT_HANDLERS` via `apply_intent`.

## LLM Validation Commands

Use this exact command after state-manager edits:

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

If you changed websocket behavior, additionally run:

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
| State bootstrap fields or shared state flags | `backend/store/state_manager/core/bootstrap.py` | state-manager validation command above |
| Fixture load/save, arm defaults, POI fixture target persistence | `backend/store/state_manager/core/fixture_store.py`, `backend/store/state_manager/core/fixture_effects.py` | state-manager validation command above |
| Song metadata length inference or metadata path resolution | `backend/store/state_manager/core/metadata.py`, `backend/store/services/song_metadata_loader.py` | state-manager validation command above + `tests/test_song_sections_payload_schema.py` + `tests/test_song_analysis_payload_chords.py` |
| Cue-sheet-to-canvas render wiring or preview render wiring | `backend/store/state_manager/core/render.py`, `backend/store/services/canvas_rendering.py` | state-manager validation command above |
| Fixture effect contracts or preview support | `backend/models/fixtures/**/*`, `backend/store/state_manager/core/fixture_effects.py`, `backend/store/state_manager/playback/preview_start.py` | state-manager validation command above + `tests/test_fixture_effect_preview_matrix.py` + `tests/test_fixture_effect_canvas_matrix.py` |
| Song load, cue persistence, section persistence | `backend/store/state_manager/song/loading.py`, `backend/store/state_manager/song/cues.py`, `backend/store/state_manager/song/sections.py` | state-manager validation command above |
| Playback transport or timecode/frame application | `backend/store/state_manager/playback/transport.py` | state-manager validation command above + `tests/test_ws_transport_jump_to_section_e2e.py` |
| Chaser preview start/stop/runner behavior | `backend/store/state_manager/playback/preview_chaser.py` | state-manager validation command above + `tests/test_chaser_preview_lifecycle.py` |
| Fixture live value write behavior | `backend/api/intents/fixture/actions/set_values.py`, `backend/store/state_manager/playback/channels.py` | state-manager validation command above + `tests/test_set_values_regression.py` |
| Snapshot or patch payload schema | `backend/api/state/*`, `backend/api/websocket_manager/broadcasting.py` | `tests/test_payload.py` |
| Chaser timing, lifecycle, or handler behavior | `backend/store/state_manager/playback/*`, `backend/api/intents/chaser/*`, `backend/services/cue_helpers/*` | state-manager validation command above + websocket validation command above |
| Cue intent or persistence behavior | `backend/api/intents/cue/*`, `backend/store/state_manager/song/cues.py` | state-manager validation command above + `tests/test_cue_add.py` + `tests/test_cue_clear.py` + `tests/test_cue_intents.py` + `tests/test_ws_cue_e2e.py` |
| Websocket intent/message behavior | `backend/api/websocket_manager/*`, `backend/api/intents/*` | websocket validation command above |
| Import path or module composition for state manager | `backend/store/state.py`, `backend/store/state_manager/manager.py` | state-manager validation command above |
