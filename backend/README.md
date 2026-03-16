# Backend Module (LLM Guide)

FastAPI + asyncio runtime responsible for authoritative show state and Art-Net output.

## Purpose

- Expose the websocket control plane at `/ws`.
- Expose a read-only vulnerability catalog at `/vulnerabilities`.
- Keep backend-authoritative state (`system`, `playback`, `fixtures`, `song`, `pois`, `cues`, `cue_helpers`).
- Render cue sheets into DMX frames and drive Art-Net output.

## Primary entrypoints

- `main.py`: lifecycle wiring, startup loading, route setup.
- `api/vulnerabilities.py`: structured catalog of backend vulnerabilities exposed by the HTTP route.
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

## Runtime model

1. Startup loads POIs and fixtures, applies arm defaults, starts Art-Net loop, then loads a default song.
2. Song load pre-renders a full `60 FPS` DMX canvas.
3. During playback, backend advances timecode with a server-side ticker and pushes Art-Net frames continuously.
4. Clients send websocket `intent` messages.
5. Backend mutates state, then emits `snapshot` or throttled `patch` updates.

## HTTP routes

- `/`: backend identifier payload.
- `/vulnerabilities`: returns the current structured list of backend vulnerabilities with severity, affected surfaces, evidence, and remediation guidance.

## WebSocket protocol essentials

### Client → Backend

- `hello`
- `intent`: `{ type:"intent", req_id, name, payload }`

Supported intent names:
- Transport: `transport.play`, `transport.pause`, `transport.stop`, `transport.jump_to_time`, `transport.jump_to_section`.
- Fixture: `fixture.set_arm`, `fixture.set_values`, `fixture.preview_effect`, `fixture.stop_preview`.
- Cue: `cue.add`, `cue.update`, `cue.delete`.
- Cue helpers: `cue.apply_helper`.
- POI: `poi.create`, `poi.update`, `poi.delete`, `poi.update_fixture_target`.
- LLM: `llm.send_prompt`, `llm.cancel`.

### Backend → Client

- `snapshot`: `{ type:"snapshot", seq, state }`
- `patch`: `{ type:"patch", seq, changes }`
- `event`: `{ type:"event", level, message, data? }`

Patch behavior:
- Diffs are currently top-level replacements only.
- `changes[].path` is one key deep (for example `[`system`]`, `[`fixtures`]`).
- While playback is `playing`, backend suppresses `fixtures` patches.

## Playback and editing behavior

- Browser audio timeline periodically aligns backend timecode (default 10s sync).
- Backend playback ticker is authoritative for frame-by-frame progression while `playing`.
- Clients can send `transport.jump_to_section` with `payload.section_index` to seek to the matching section start.
- Section boundaries and labels are resolved from normalized section fields (`start_s|start`, `end_s|end`, `name|label`).
- `fixture.preview_effect` is rejected while playback is active. Preview runs to completion and final effect values persist to `editor_universe` (and `output_universe`).
- `fixture.set_values` applies live channel updates via Art-Net using fixture meta-channel mappings. For `kind="rgb"` meta-channels, send `values.rgb` as `#RRGGBB` (or mapped color name); backend converts it to channel bytes.
- Cue edits support add/update/delete by index via `cue.add`, `cue.update`, and `cue.delete` intents.
- `transport.stop` always applies blackout (`output_universe` all zeros) before Art-Net update.
- `cue.apply_helper` generates cue entries from song beats and upserts into cue sheet.

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

Section payload normalization:
- Backend accepts analyzer section records with either `start/end/label` or `start_s/end_s/name` keys.
- Snapshot payload always emits normalized section entries as `{name, start_s, end_s}`.

## Reference docs

- [Backend implementation reference](../docs/architecture/backend_llm_reference.md)
- [Backend architecture narrative](../docs/architecture/backend.md)
- [Backend fixture schema](../docs/architecture/backend_fixtures_schema.md)
- [Backend POI schema](../docs/architecture/backend_pois_schema.md)

## Development

```bash
pyenv activate ai-light
cd backend
pip install -r requirements.txt
python main.py
```

Default local URL: `http://localhost:5001`.

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
	tests/test_preview_lifecycle_regression.py \
	tests/test_metadata_sections_regression.py \
	tests/test_dmx_canvas_render_new.py \
	tests/test_fixture_loading_new.py \
	tests/test_payload.py
```

## LLM Change Matrix

Use this matrix to pick edit targets and minimum tests quickly:

| If you change... | Edit here first | Then run... |
| --- | --- | --- |
| State bootstrap fields or shared state flags | `store/state_manager/core/bootstrap.py` | state-manager regression command above |
| Fixture load/save, arm defaults, POI fixture target persistence | `store/state_manager/core/fixture_store.py`, `store/state_manager/core/fixture_effects.py` | state-manager regression command above |
| Song metadata length inference or metadata path resolution | `store/state_manager/core/metadata.py`, `store/services/song_metadata_loader.py` | state-manager regression command above + `tests/test_metadata_sections_regression.py` |
| Cue-sheet-to-canvas render wiring or preview render wiring | `store/state_manager/core/render.py`, `store/services/canvas_rendering.py` | state-manager regression command above |
| Song load, cue persistence, section persistence | `store/state_manager/song/loading.py`, `store/state_manager/song/cues.py`, `store/state_manager/song/sections.py` | state-manager regression command above |
| Playback transport or timecode/frame application | `store/state_manager/playback/transport.py` | state-manager regression command above |
| Preview start/stop/runner behavior | `store/state_manager/playback/preview_start.py`, `store/state_manager/playback/preview_control.py`, `store/state_manager/playback/preview_runner.py` | state-manager regression command above + `tests/test_preview_lifecycle_regression.py` |
| Fixture live value write behavior | `api/intents/fixture/actions/set_values.py`, `store/state_manager/playback/channels.py` | state-manager regression command above + `tests/test_set_values_regression.py` |
| Snapshot or patch payload schema | `api/state/*`, `api/websocket_manager/broadcasting.py` | `tests/test_payload.py` |
| Websocket intent/message behavior | `api/websocket_manager/*`, `api/intents/*` | `PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q tests/test_ws_poi_e2e.py` |
| Import path or module composition for state manager | `store/state.py`, `store/state_manager/manager.py` | state-manager regression command above |

## LLM contributor checklist

1. Keep protocol docs aligned with current handler behavior.
2. Keep intent names synchronized with `INTENT_HANDLERS`.
3. When effect contracts change, update docs and client integrations in the same change.
4. Preserve deterministic render behavior at `60 FPS`.
