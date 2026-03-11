# Backend LLM Reference (Code-Accurate)

This document is an implementation-level reference for backend behavior in `backend/`.
Code is the source of truth.

## Runtime map

1. App bootstrap: `backend/main.py`
- Creates `StateManager`, `ArtNetService`, `SongService`, `WebSocketManager`.
- Loads POIs and fixtures.
- Arms fixtures and starts Art-Net send loop.
- Loads default song (`Yonaka - Seize the Power` if present, else first available).
- Mounts songs at `/songs` and exposes websocket endpoint at `/ws`.

2. WebSocket transport: `backend/api/websocket_manager/*`
- `endpoint.py`: accepts and reads websocket frames.
- `messaging.py`: parses incoming frames and dispatches intents.
- `broadcasting.py`: throttled patch broadcast (`50ms` min interval).
- `manager.py`: shared state (`seq`, active connections, fixture arm cache).

3. Intent routing: `backend/api/intents/*`
- `apply_intent.py` dispatches by domain via `INTENT_HANDLERS`.
- Domains: `transport`, `fixture`, `poi`, `llm`.

4. State authority: `backend/store/state.py`
- Holds fixtures, POIs, song/cue state, playback flags, preview lifecycle.
- Delegates fixture/template loading, song metadata resolution, section persistence, and canvas rendering helpers to `backend/store/services/*`.
- Pre-renders full song DMX canvas at `60 FPS`.
- Computes output frame from synchronized timecode.

5. DMX output: `backend/services/artnet.py`
- Maintains active DMX universe.
- Sends Art-Net packets on loop.
- Sends only on change unless `continuous_send=True`.

## Behavior-critical modules and symbols

| Module | Key symbols | Runtime responsibility |
| --- | --- | --- |
| `backend/main.py` | `lifespan`, `websocket_route` | Startup/shutdown wiring and route exposure |
| `backend/api/websocket_manager/manager.py` | `WebSocketManager` | Connection registry, sequencing, orchestration |
| `backend/api/websocket_manager/messaging.py` | `handle_message`, `send_snapshot`, `broadcast_event` | Protocol handling and message emission |
| `backend/api/websocket_manager/broadcasting.py` | `schedule_broadcast`, `broadcast_patch` | Throttled state-diff broadcasting |
| `backend/api/intents/apply_intent.py` | `apply_intent` | Intent dispatch and unknown-intent warning events |
| `backend/api/state/build_frontend_state.py` | `build_frontend_state` | Canonical snapshot/patch state payload |
| `backend/api/state/fixtures.py` | `build_fixtures_payload` | Fixture state serialization |
| `backend/api/state/song_payload.py` | `build_song_payload` | Song metadata payload normalization |
| `backend/store/state.py` | `StateManager` | Core show state + render + preview + persistence |
| `backend/store/services/fixture_loader.py` | `load_fixtures_from_path` | Fixture/template loading and instantiation |
| `backend/store/services/song_metadata_loader.py` | `SongMetadataLoader` | Metadata candidate resolution + beats/downbeats hydration |
| `backend/store/services/section_persistence.py` | `normalize_sections_input`, `persist_parts_to_meta` | Section validation and metadata persistence |
| `backend/store/services/canvas_rendering.py` | `render_cue_sheet_to_canvas`, `render_preview_canvas`, `dump_canvas_debug` | DMX canvas rendering + debug log dump |
| `backend/store/services/canvas_render_core.py` | `iter_cues_for_render`, `render_entry_into_universe` | Cue iteration and per-entry frame rendering helpers |
| `backend/store/services/canvas_debug.py` | `dump_canvas_debug` | Canvas debug file writer |
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
- Current diff granularity is top-level key replacement only (`system`, `playback`, `fixtures`, `song`, `pois`).

3. `event`
- Shape: `{"type":"event","level":"info|warning|error","message":string,"data"?:object}`

## Intent catalog (current implementation)

### Transport intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `transport.play` | none | `set_playback_state(True)`, enable continuous Art-Net send | `True` |
| `transport.pause` | none | `set_playback_state(False)`, disable continuous send | `True` |
| `transport.stop` | none | pause + seek `0` + push current output universe + disable continuous send | `True` |
| `transport.jump_to_time` | `time_ms` | seek to `max(0, time_ms/1000)` and push output universe | `True` on valid time, else event `invalid_time_ms` and `False` |
| `transport.jump_to_section` | none | not implemented | event `jump_to_section_not_implemented`, returns `False` |

### Fixture intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `fixture.set_arm` | `fixture_id`, `armed` | updates `manager.fixture_armed` only | `True` if `fixture_id` present, else event `fixture_id_required` and `False` |
| `fixture.set_values` | `fixture_id`, `values` | updates fixture `current_values` and applies mapped DMX channel writes to `ArtNetService` | `True` if any channel write applied |
| `fixture.preview_effect` | `fixture_id`, `effect_id`, `duration_ms`, `params` | validates and starts preview canvas playback | `True` on success; else event `preview_rejected` and `False` |
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

### LLM intents

| Intent | Payload keys | Behavior | Returns |
| --- | --- | --- | --- |
| `llm.send_prompt` | `prompt` | emits `llm_stream` chunks (`Echo: ` + prompt) | `False` (no patch broadcast) |
| `llm.cancel` | none | emits `llm_cancelled` | `False` |

## Event message catalog

| Level | Message | `data` payload |
| --- | --- | --- |
| `error` | `invalid_json` | none |
| `warning` | `unsupported_message_type` | `{type: <received type>}` |
| `warning` | `unknown_intent` | `{name}` |
| `error` | `invalid_time_ms` | none |
| `warning` | `jump_to_section_not_implemented` | none |
| `error` | `fixture_id_required` | none |
| `warning` | `preview_rejected` | rejection object from `start_preview_effect` |
| `info` | `preview_started` | preview result object (`requestId`, `fixtureId`, `effect`, `duration`) |
| `warning` | `stop_preview_not_implemented` | none |
| `error` | `prompt_required` | none |
| `info` | `llm_stream` | `{domain:"llm", chunk, done}` |
| `info` | `llm_cancelled` | `{domain:"llm"}` |

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
      "mappings": {}
    }
  },
  "song": {
    "filename": "Song",
    "audio_url": "/songs/Song.mp3",
    "length_s": 180,
    "bpm": 120,
    "sections": [{"name": "intro", "start_s": 0.0, "end_s": 12.5}],
    "beats": [0.5, 1.0],
    "downbeats": [0.5, 2.5],
    "analysis": {
      "plots": [{"id": "rhythm", "title": "Rhythm", "svg_url": "/meta/Song/essentia/rhythm.svg"}],
      "chords": [{"time_s": 12.0, "label": "Fm", "bar": 8, "beat": 1}]
    }
  },
  "pois": []
}
```

Field notes:
- `system.edit_lock` is `True` when playback is active.
- `playback.state` derives from `isPlaying` plus `timecode` (`stopped` only at ~0).
- `song` is `null` when no song is loaded.
- `song.analysis` is optional and is present only when analysis artifacts exist for the loaded song.
- For RGB fixtures, `fixtures.<id>.values.rgb` is emitted as canonical uppercase `#RRGGBB`.

## Effect data contracts

### Moving head effects

| Effect | Required/expected `data` keys | Behavior |
| --- | --- | --- |
| `set_channels` | `channels` object | instant write at start frame |
| `move_to` | pan/tilt targets (`pan`/`tilt` u16 or axis byte variants/preset) | interpolates pan/tilt across cue duration |
| `move_to_poi` | `target_POI` (also accepts `poi` or `POI`) | interpolates toward POI target for this fixture |
| `seek` | same target parsing as `move_to` | instant pan/tilt set at start frame |
| `strobe` | optional `rate` (Hz) | toggles shutter/dimmer channel |
| `full` | none | instant full-on dimmer (+ shutter if available) |
| `flash` | none | fades dimmer from 255 to 0 over duration |
| `sweep` | required `subject_POI`, `start_POI`; optional `end_POI`, `duration`, `easing`, `arc_strength`, `subject_close_ratio`, `max_dim` | two-leg arc sweep with dimmer shaping around subject POI |

### Parcan effects

| Effect | Required/expected `data` keys | Behavior |
| --- | --- | --- |
| `set_channels` | `channels` object | instant write at start frame |
| `flash` | optional `channels` list | fades selected channels (default RGB) |
| `strobe` | optional `rate` or `speed` | toggles RGB between cached "on" color and off |
| `fade_in` | any of `red`, `green`, `blue` | interpolates from current RGB to targets |
| `full` | optional `red`, `green`, `blue` | instant RGB set (default white) |

## Notes on legacy wrappers

- `backend/api/websocket.py` re-exports websocket manager entrypoints.
- `backend/api/ws_handlers.py` and `backend/api/ws_state_builder.py` are compatibility exports.
- Domain `router.py` files exist but main dispatch uses `INTENT_HANDLERS` via `apply_intent`.
