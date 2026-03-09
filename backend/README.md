# Backend Module (LLM Guide)

FastAPI + asyncio runtime responsible for authoritative show state and Art-Net output.

## Purpose

- Expose the websocket control plane at `/ws`.
- Keep backend-authoritative state (`system`, `playback`, `fixtures`, `song`, `pois`).
- Render cue sheets into DMX frames and drive Art-Net output.

## Primary entrypoints

- `main.py`: lifecycle wiring, startup loading, route setup.
- `api/websocket_manager/*`: websocket endpoint, message parsing, broadcasts, sequencing.
- `api/intents/*`: intent handlers and registry.
- `api/state/*`: snapshot/patch payload builders.
- `store/state.py`: `StateManager` (fixtures, cues, playback, preview, canvas).
- `store/services/*`: `StateManager` collaborators for fixture loading, metadata loading, section persistence, and canvas rendering/debug output.
- `store/pois.py`: POI CRUD + persistence.
- `store/dmx_canvas.py`: packed DMX frame buffer.
- `services/artnet.py`: UDP Art-Net sender.

## Runtime model

1. Startup loads POIs and fixtures, applies arm defaults, starts Art-Net loop, then loads a default song.
2. Song load pre-renders a full `60 FPS` DMX canvas.
3. Clients send websocket `intent` messages.
4. Backend mutates state, then emits `snapshot` or throttled `patch` updates.

## WebSocket protocol essentials

### Client → Backend

- `hello`
- `intent`: `{ type:"intent", req_id, name, payload }`

Supported intent names:
- Transport: `transport.play`, `transport.pause`, `transport.stop`, `transport.jump_to_time`, `transport.jump_to_section`.
- Fixture: `fixture.set_arm`, `fixture.set_values`, `fixture.preview_effect`, `fixture.stop_preview`.
- POI: `poi.create`, `poi.update`, `poi.delete`, `poi.update_fixture_target`.
- LLM: `llm.send_prompt`, `llm.cancel`.

### Backend → Client

- `snapshot`: `{ type:"snapshot", seq, state }`
- `patch`: `{ type:"patch", seq, changes }`
- `event`: `{ type:"event", level, message, data? }`

Patch behavior:
- Diffs are currently top-level replacements only.
- `changes[].path` is one key deep (for example `[`system`]`, `[`fixtures`]`).

## Playback and editing behavior

- Browser audio timeline is authoritative for timecode sync.
- Clients should send `transport.jump_to_time` periodically during playback and on immediate transport changes.
- `fixture.preview_effect` is rejected while playback is active.
- `fixture.set_values` applies live channel updates via Art-Net using fixture meta-channel mappings.

## Data and file contracts

- Fixtures: `backend/fixtures/fixtures.json`
- Fixture templates: `backend/fixtures/fixture.<type>.<model>.json`
- POIs: `backend/fixtures/pois.json`
- Cues: `backend/cues/{song}.cue.json`
- Songs: `backend/songs/*.mp3`
- Metadata root in Docker: `/app/meta` (fallback local: `backend/meta`)

## Reference docs

- [Backend implementation reference](../docs/architecture/backend_llm_reference.md)
- [Backend architecture narrative](../docs/architecture/backend.md)
- [Backend fixture schema](../docs/architecture/backend_fixtures_schema.md)
- [Backend POI schema](../docs/architecture/backend_pois_schema.md)

## Development

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Default local URL: `http://localhost:5001`.

## LLM contributor checklist

1. Keep protocol docs aligned with current handler behavior.
2. Keep intent names synchronized with `INTENT_HANDLERS`.
3. When effect contracts change, update docs and client integrations in the same change.
4. Preserve deterministic render behavior at `60 FPS`.
