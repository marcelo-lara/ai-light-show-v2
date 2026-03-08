# Tests Module (LLM Guide)

Project-level Python tests for backend state/render behavior and related integration checks.

## Test suite contents

- `tests/test_fixture_loading_new.py`: fixture template loading and channel mapping.
- `tests/test_dmx_canvas_render_new.py`: cue rendering to DMX canvas.
- `tests/test_poi_database.py`: POI CRUD persistence.
- `tests/test_payload.py`: fixture payload shape smoke check.

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
