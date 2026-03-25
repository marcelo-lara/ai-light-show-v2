# Tests Module (LLM Guide)

Project-level Python tests for backend state/render behavior, websocket intent flows, and file-backed integration checks.

## Test suite contents

- Fixture loading and render paths:
	- `tests/test_fixture_loading_new.py`: fixture template loading and absolute channel mapping.
	- `tests/test_dmx_canvas_render_new.py`: effect and chaser cue rendering into the DMX canvas.
	- `tests/test_fixture_effect_canvas_matrix.py`: DMX canvas rendering coverage for every declared effect on every fixture template in use.
	- `tests/test_fixture_effect_preview_matrix.py`: preview coverage for every declared effect on every fixture template in use.
	- `tests/test_payload.py`: fixture payload serialization and `state.chasers` snapshot payload coverage.
- Cue persistence and intent behavior:
	- `tests/test_cue_add.py`: cue add/load/update/delete coverage for effect and chaser rows.
	- `tests/test_cue_clear.py`: cue sheet clearing and deletion behavior.
	- `tests/test_cue_intents.py`: websocket intent handler coverage for `cue.update`, `cue.delete`, `cue.clear`, and `cue.apply_helper`.
	- `tests/test_ws_cue_e2e.py`: real-file websocket cue update/delete flow with restore.
- Preview and live value behavior:
	- `tests/test_set_values_regression.py`: `fixture.set_values` coverage for `u8`, `u16`, `enum`, and `rgb` meta-channel behavior.
- Chaser behavior:
	- `tests/test_chaser_timing.py`: beat-to-time conversion helpers.
	- `tests/test_chaser_intents.py`: `chaser.apply|preview|start|stop|list` handler behavior.
	- `tests/test_chaser_preview_lifecycle.py`: chaser preview lock policy, cleanup, and persisted chaser row behavior.
	- `tests/test_ws_chaser_e2e.py`: real-file websocket chaser apply/start/stop flows with restore.
	- `tests/test_ws_chaser_preview_e2e.py`: non-persistent websocket chaser preview flow.
- Song analysis and transport behavior:
	- `tests/test_backend_mcp_server.py`: backend-mounted MCP tool coverage for songs, metadata, and cue window/replace flows.
	- `tests/test_song_sections_payload_schema.py`: section payload normalization (`start/end/label` -> `{name,start_s,end_s}`).
	- `tests/test_song_analysis_payload_chords.py`: chord payload parsing, `N` retention, and de-duplication behavior.
	- `tests/test_jump_to_section_regression.py`: backend `transport.jump_to_section` validation and seek behavior.
	- `tests/test_ws_transport_jump_to_section_e2e.py`: websocket section jump flow and playback time updates.
- POI behavior:
	- `tests/test_poi_database.py`: POI CRUD and fixture target persistence.
	- `tests/test_ws_poi_e2e.py`: real-file websocket POI persistence flow with restore.

## Test file location policy

- Keep automated Python tests under `tests/`.
- Do not keep `test_*.py` files at repo root.

## Run tests

Use the project Python environment (`ai-light`) and include repo + backend on `PYTHONPATH`:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q
```

Routine run without file-mutating e2e coverage:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q -m "not e2e_real_file"
```

Collect-only check:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest --collect-only -q
```

Opt-in real-file e2e tests:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q -m e2e_real_file tests/test_ws_poi_e2e.py
```

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q -m e2e_real_file \
	tests/test_ws_poi_e2e.py \
	tests/test_ws_cue_e2e.py \
	tests/test_ws_chaser_e2e.py \
	tests/test_ws_chaser_preview_e2e.py
```

## Expected workflow

1. Run targeted tests for touched modules.
2. Run `-m "not e2e_real_file"` for broader protocol/state regression coverage.
3. Rebuild/restart containers before manual validation when needed:

```bash
docker compose down && docker compose up --build -d
```

## LLM contributor checklist

1. Keep tests colocated in `tests/`.
2. Avoid unrelated rewrites.
3. If protocol/data contracts change, update tests in the same change.
4. Keep fixtures deterministic and avoid flaky timing assumptions.
5. `e2e_real_file` tests mutate repo-tracked cue and POI files, restore them afterward, and are non-parallel-safe by design.
