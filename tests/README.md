# Tests Module (LLM Guide)

Project-level Python tests for backend state/render behavior and related integration checks.

## Test suite contents

- `tests/test_fixture_loading_new.py`: fixture template loading and channel mapping.
- `tests/test_dmx_canvas_render_new.py`: cue rendering to DMX canvas.
- `tests/test_poi_database.py`: POI CRUD persistence.
- `tests/test_payload.py`: fixture payload shape smoke check.
- `tests/test_song_sections_payload_schema.py`: song section payload normalization (`start/end/label` -> `{name,start_s,end_s}`).
- `tests/test_jump_to_section_regression.py`: backend `transport.jump_to_section` index validation and seek behavior.
- `tests/test_ws_transport_jump_to_section_e2e.py`: websocket intent flow for section jumps and playback time updates.
- `tests/test_ws_poi_e2e.py`: websocket frontend-mimic integration test for POI persistence on real `backend/fixtures/pois.json` with auto-restore.

## Test file location policy

- Keep automated Python tests under `tests/`.
- Do not keep `test_*.py` files at repo root.

## Run tests

Use the project Python environment (`ai-light`) and include repo + backend on `PYTHONPATH`:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q
```

Collect-only check:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest --collect-only -q
```

Opt-in real-file e2e test:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q -m e2e_real_file tests/test_ws_poi_e2e.py
```

## Expected workflow

1. Run targeted tests for touched modules.
2. Run broader regression suite for protocol/state contract changes.
3. Rebuild/restart containers before manual validation when needed:

```bash
docker compose down && docker compose up --build -d
```

## LLM contributor checklist

1. Keep tests colocated in `tests/`.
2. Avoid unrelated rewrites.
3. If protocol/data contracts change, update tests in the same change.
4. Keep fixtures deterministic and avoid flaky timing assumptions.
5. `e2e_real_file` tests are non-parallel-safe by design; run them in isolation.
