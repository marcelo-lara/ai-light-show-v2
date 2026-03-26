# Backend Module (LLM Guide)

FastAPI + asyncio runtime responsible for authoritative show state and Art-Net output.

## Purpose

- Expose the websocket control plane at `/ws`.
- Expose a backend-owned MCP tool surface at `/mcp`.
- Keep backend-authoritative state (`system`, `playback`, `fixtures`, `song`, `pois`, `cues`, `cue_helpers`, `chasers`).
- Render cue sheets into DMX frames and drive Art-Net output.

## Primary entrypoints

- `main.py`: lifecycle wiring, startup loading, route setup.
- `mcp_server/*`: mounted MCP tools for songs, fixtures, cues, and song metadata.
- `api/websocket_manager/*`: websocket endpoint, message parsing, broadcasts, sequencing.
- `api/intents/*`: intent handlers and registry.
- `api/state/*`: snapshot/patch payload builders.
- `store/state.py`: compatibility export for `StateManager`, `FPS`, and `MAX_SONG_SECONDS`.
- `store/state_manager/core/*`: bootstrap state fields, fixture/POI store operations, metadata helpers, canvas render wrappers.
- `store/state_manager/song/*`: song load + cue and section persistence operations.
- `store/state_manager/playback/*`: transport, preview lifecycle, channel edits, and frame application.
- `store/services/*`: `StateManager` collaborators for fixture loading, metadata loading, section persistence, and canvas rendering/debug output.
- `store/pois.py`: POI CRUD + persistence.
- `store/dmx_canvas.py`: packed DMX frame buffer.
- `services/artnet.py`: UDP Art-Net sender.
- `services/assistant/*`: assistant profile storage, gateway client, request lifecycle, and confirmation-gated LLM orchestration.

## Runtime model

1. Startup loads POIs and fixtures, applies arm defaults, starts Art-Net loop, then loads a default song.
2. Song load pre-renders a full `60 FPS` DMX canvas.
3. During playback, backend advances timecode with a server-side ticker and pushes Art-Net frames continuously.
4. Clients send websocket `intent` messages.
5. Backend mutates state, then emits `snapshot` or throttled `patch` updates.
6. MCP clients call backend-owned tools over Streamable HTTP and share the same live runtime state.

## WebSocket protocol essentials

### Client → Backend

- `hello`
- `intent`: `{ type:"intent", req_id, name, payload }`

Supported intent names:
- Song: `song.list`, `song.load`.
- Transport: `transport.play`, `transport.pause`, `transport.stop`, `transport.jump_to_time`, `transport.jump_to_section`.
- Fixture: `fixture.set_arm`, `fixture.set_values`, `fixture.preview_effect`, `fixture.stop_preview`.
- Cue: `cue.add`, `cue.update`, `cue.delete`, `cue.clear`.
- Cue helpers: `cue.apply_helper`.
- Chaser: `chaser.apply`, `chaser.preview`, `chaser.stop_preview`, `chaser.start`, `chaser.stop`, `chaser.list`.
- POI: `poi.create`, `poi.update`, `poi.delete`, `poi.update_fixture_target`.
- LLM: `llm.send_prompt`, `llm.cancel`.
- LLM confirmation: `llm.confirm_action`, `llm.reject_action`.

## MCP protocol essentials

- Mounted endpoint: `/mcp`
- Transport: Streamable HTTP
- Mode: stateless HTTP with JSON responses

Current MCP tools:
- Songs: `songs_list`, `songs_get_details`, `songs_load`
- Fixtures: `fixtures_list`, `fixtures_get`, `chasers_list`
- Cues: `cues_get_sheet`, `cues_get_window`, `cues_add_entry`, `cues_update_entry`, `cues_delete_entry`, `cues_replace_sheet`
- Metadata: `metadata_get_overview`, `metadata_get_sections`, `metadata_find_section`, `metadata_get_beats`, `metadata_get_bar_beats`, `metadata_find_bar_beat`, `metadata_get_chords`, `metadata_find_chord`, `metadata_get_loudness`
- Transport: `transport_get_cursor`

Behavior notes:
- MCP song and cue mutation tools operate on the same `StateManager` used by websocket clients.
- MCP mutations schedule websocket patch broadcasts so connected UI clients stay in sync.
- Metadata tools expose analyzer beat positions as bars and beats, including section start/end positions and exact bar/beat lookup.
- Loudness summaries are read from analyzer `essentia/loudness_envelope.json` artifacts and returned as averaged window statistics.

### Backend → Client

- `snapshot`: `{ type:"snapshot", seq, state }`
- `patch`: `{ type:"patch", seq, changes }`
- `event`: `{ type:"event", level, message, data? }`

Assistant event behavior:
- Assistant replies are session-scoped websocket events and are not broadcast globally to other clients.
- Assistant requests include recent per-client user and assistant turns from the current websocket session so follow-up prompts can reference the prior exchange.
- `llm_status` carries operational system messages such as `Thinking`, `Calling local model`, or `Executing metadata_get_sections`.
- `llm_delta` carries streamed assistant text chunks.
- `llm_done` closes the active streamed assistant response.
- `llm_action_proposed` carries confirmation-gated write proposals for cue or chaser mutations.
- `llm_action_applied`, `llm_action_rejected`, `llm_cancelled`, and `llm_error` report assistant request lifecycle outcomes.
- Assistant interactions are appended to JSONL logs under `ASSISTANT_LOG_DIR` (Docker default `/app/logs/assistant`, host path `backend/logs/assistant`) so failed manual runs can be replayed from the prompt, streamed gateway events, proposals, confirmations, and emitted client events.

Patch behavior:
- Diffs are currently top-level replacements only.
- `changes[].path` is one key deep (for example `[`system`]`, `[`fixtures`]`).
- While playback is `playing`, backend suppresses `fixtures` patches.

## Playback and editing behavior

- Browser audio timeline periodically aligns backend timecode (default 10s sync).
- Backend playback ticker is authoritative for frame-by-frame progression while `playing`.
- `song.list` emits the currently loadable backend song names without mutating state.
- `song.load` validates `payload.filename`, loads the selected song into backend state, resets playback to stopped, updates the output universe, and schedules a snapshot/patch broadcast.
- `songs_load` on the MCP surface applies the same load side effects: load state, stop playback ticker, disable continuous send, push the output universe, then schedule websocket broadcasts.
- Clients can send `transport.jump_to_section` with `payload.section_index` to seek to the matching section start.
- Section boundaries and labels are resolved from normalized section fields (`start_s|start`, `end_s|end`, `name|label`).
- `fixture.preview_effect` is rejected while playback is active. Preview runs to completion and final effect values persist to `editor_universe` (and `output_universe`).
- `fixture.set_values` applies live channel updates via Art-Net using fixture meta-channel mappings. For `kind="rgb"` meta-channels, send `values.rgb` as `#RRGGBB` (or mapped color name); backend converts it to channel bytes.
- Cue edits support add/update/delete by index via `cue.add`, `cue.update`, and `cue.delete` intents.
- `cue.clear` removes cue entries from a time window: `from_time` only clears all entries at or after that time, and `from_time` + `to_time` clears entries inside the inclusive range.
- `cue.clear_all` removes every entry from the current cue sheet.
- Cue writes de-duplicate identical effect rows (`fixture_id` + `effect`) and identical chaser rows (`chaser_id`) within a `100ms` window; the latest write replaces the earlier row instead of appending a duplicate.
- `llm.send_prompt` starts an assistant request through the backend-owned assistant service. The assistant service loads a named prompt profile, includes recent per-client chat history from the current websocket session, forwards the request to the agent gateway, relays streamed model output to the requesting websocket client, and pauses write-capable tool calls at the proposal stage.
- `llm.confirm_action` applies a proposed cue or chaser mutation after explicit user confirmation, schedules a broadcast for the resulting state change, and then emits a backend-generated completion summary for that executed action.
- `llm.reject_action` dismisses a pending proposal without mutating cues.
- `transport.stop` always applies blackout (`output_universe` all zeros) before Art-Net update.
- `cue.apply_helper` generates cue entries from song beats and upserts into cue sheet.
- `chaser.apply` and `chaser.start` persist chaser-backed cue rows from `backend/fixtures/chasers.json`.
- `chaser.preview` renders chaser effects as a temporary non-persistent output stream.
- `chaser.stop_preview` stops temporary chaser preview output without writing cues.
- Chaser effect fields `beat` and `duration` are beat-based and converted with `beatToTimeMs(beat_count, bpm)`.
- Moving-head `strobe` is dimmer-driven only. Dedicated fixture `strobe` and `shutter` channels are not modulated by the effect handler.
- Moving-head `seek` computes dark pre-roll from the previous pan/tilt position to `start_POI` using the fixture template `physical_movement` timing plus `100 ms` safety and `100 ms` settle time. During the visible effect it orbits around `subject_POI` from `start_POI`, spirals into the subject by cue end, and clamps per-frame pan/tilt moves to the fixture's maximum physical travel. `orbits` controls turn count, and `easing` controls how long the head stays wide before tightening: `late_focus` is the recommended default, `balanced` is neutral, `linear` is mechanical, and `early_focus` collapses quickly.
- `sweep` schedules a dark pre-roll based on the fixture's previous pan/tilt position and the template's `physical_movement.pan_full_travel_seconds` / `physical_movement.tilt_full_travel_seconds` metadata, plus an extra `100 ms` safety pre-roll. During that pre-roll the head moves to `start_POI`, holds there dark for `100 ms`, then runs cubic ease-out into `subject_POI`, cubic ease-in away from the subject, and an independent mirrored dimmer envelope. Visible pan/tilt motion is also clamped per frame to the fixture's maximum physical travel, so short sweep durations can lag the ideal geometric path on slower fixtures. `dimmer_easing` is a normalized `0..1` control for how late fade-in begins before the subject, and `max_dim` is guaranteed when pan/tilt land on the subject POI.
- Cue sheets store mixed entries:
  - effect row: `time`, `fixture_id`, `effect`, `duration`, `data`, `name`, `created_by`
  - chaser row: `time`, `chaser_id`, `data`, `name`, `created_by`
- Chaser rows store `data.repetitions` and are expanded into effect renders only at canvas/preview time.
- Persisted chaser rows use `created_by` set to `chaser:{id}`.

## Data and file contracts

- Fixtures: `backend/fixtures/fixtures.json`
- Fixture templates: `backend/fixtures/fixture.<type>.<model>.json`
- POIs: `backend/fixtures/pois.json`
- Cues: `backend/cues/{song}.json`
- Songs: `backend/songs/*.mp3`
- Metadata root in Docker: `/app/meta` (fallback local: `backend/meta`)
- Static routes: `/songs/*` for audio and `/meta/*` for analyzer artifacts (SVG/JSON).

Song payload fields under `state.song`:
- Core: `filename`, `audio_url`, `length_s`, `bpm`, `sections`, `beats`.
- Optional analysis: `analysis.plots[]` (`id`, `title`, `svg_url`) and `analysis.chords[]` (`time_s`, `label`, optional `bar`/`beat`).

Cue helpers payload under `state.cue_helpers`:
- List of helper definitions (`id`, `label`, `description`, `mode`) for frontend helper UI.

MCP cue payloads:
- `cues_get_sheet` returns the full persisted cue sheet for the current song.
- `cues_get_window` returns entries in an inclusive `[start_time, end_time]` window.
- `cues_replace_sheet` validates and replaces the full cue sheet, persists it, and re-renders the DMX canvas.

Chasers payload under `state.chasers`:
- List of chaser definitions loaded from `backend/fixtures/chasers.json`, including stable `id`, display `name`, `description`, and beat-based `effects`.

Section payload normalization:
- Backend accepts analyzer section records with either `start/end/label` or `start_s/end_s/name` keys.
- Snapshot payload always emits normalized section entries as `{name, start_s, end_s}`.

## Reference docs

- [Backend implementation reference](../docs/architecture/backend_llm_reference.md)
- [Backend architecture narrative](../docs/architecture/backend.md)
- [Backend fixture schema](../docs/architecture/backend_fixtures_schema.md)
- [Backend POI schema](../docs/architecture/backend_pois_schema.md)
- [Backend chasers schema](../docs/architecture/backend_chasers_schema.md)

## Development

```bash
pyenv activate ai-light
cd backend
pip install -r requirements.txt
python main.py
```

Default local URL: `http://localhost:5001`.

## Runtime Environment

- `DEBUG`: sets backend logger level (`DEBUG` when truthy, otherwise `INFO`).
- `DEBUG_MODE`: when truthy, `ArtNetService` prints sent DMX channel payloads to stdout and to a file if `DEBUG_FILE` is set.
- `DEBUG_FILE`: optional path to write Art-Net debug output to a file in addition to stdout.
- `ASSISTANT_LOG_DIR`: directory for assistant interaction JSONL logs. In Docker Compose this is `/app/logs/assistant`, persisted to `backend/logs/assistant` on the host.

## LLM Fast Map

Use this map before editing backend runtime state:
- `store/state.py`: import-safe entrypoint for callers.
- `store/state_manager/manager.py`: mixin composition order for `StateManager`.
- `store/state_manager/core/*`: initialization + fixture/POI + metadata + render helpers.
- `store/state_manager/song/*`: song/cue/sections behavior.
- `store/state_manager/playback/*`: playback transport + preview behavior.

Validation after editing `StateManager` paths:

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

Use this matrix to pick edit targets and minimum tests quickly:

| If you change... | Edit here first | Then run... |
| --- | --- | --- |
| State bootstrap fields or shared state flags | `store/state_manager/core/bootstrap.py` | state-manager regression command above |
| Fixture load/save, arm defaults, POI fixture target persistence | `store/state_manager/core/fixture_store.py`, `store/state_manager/core/fixture_effects.py` | state-manager regression command above |
| Song metadata length inference or metadata path resolution | `store/state_manager/core/metadata.py`, `store/services/song_metadata_loader.py` | state-manager regression command above + `tests/test_song_sections_payload_schema.py` + `tests/test_song_analysis_payload_chords.py` |
| Cue-sheet-to-canvas render wiring or preview render wiring | `store/state_manager/core/render.py`, `store/services/canvas_rendering.py` | state-manager regression command above |
| Fixture effect contracts or preview support | `models/fixtures/**/*`, `store/state_manager/core/fixture_effects.py`, `store/state_manager/playback/preview_start.py` | state-manager regression command above + `tests/test_fixture_effect_preview_matrix.py` + `tests/test_fixture_effect_canvas_matrix.py` |
| Song load, cue persistence, section persistence | `store/state_manager/song/loading.py`, `store/state_manager/song/cues.py`, `store/state_manager/song/sections.py` | state-manager regression command above |
| Song enumeration and load intents | `api/intents/song/*`, `services/song_service.py` | websocket/file-backed command above + `tests/test_song_intents.py` + `tests/test_ws_song_e2e.py` |
| Playback transport or timecode/frame application | `store/state_manager/playback/transport.py` | state-manager regression command above + `tests/test_ws_transport_jump_to_section_e2e.py` |
| Chaser preview start/stop/runner behavior | `store/state_manager/playback/preview_chaser.py` | state-manager regression command above + `tests/test_chaser_preview_lifecycle.py` |
| Fixture live value write behavior | `api/intents/fixture/actions/set_values.py`, `store/state_manager/playback/channels.py` | state-manager regression command above + `tests/test_set_values_regression.py` |
| Snapshot or patch payload schema | `api/state/*`, `api/websocket_manager/broadcasting.py` | `tests/test_payload.py` |
| Chaser timing, lifecycle, or handler behavior | `store/state_manager/playback/*`, `api/intents/chaser/*`, `services/cue_helpers/*` | state-manager regression command above + websocket/file-backed command above |
| Cue intent or persistence behavior | `api/intents/cue/*`, `store/state_manager/song/cues.py` | state-manager regression command above + `tests/test_cue_add.py` + `tests/test_cue_clear.py` + `tests/test_cue_intents.py` + `tests/test_ws_cue_e2e.py` |
| Websocket intent/message behavior | `api/websocket_manager/*`, `api/intents/*` | websocket/file-backed command above |
| Import path or module composition for state manager | `store/state.py`, `store/state_manager/manager.py` | state-manager regression command above |

## LLM contributor checklist

1. Keep protocol docs aligned with current handler behavior.
2. Keep intent names synchronized with `INTENT_HANDLERS`.
3. When effect contracts change, update docs and client integrations in the same change.
4. Preserve deterministic render behavior at `60 FPS`.
