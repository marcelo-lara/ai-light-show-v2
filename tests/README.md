# Tests Module (LLM Guide)

Project-level Python tests for analyzer, DMX rendering, and WebSocket behaviors.

## Test suite contents

- `test_analyzer_beat_comparison.py`: analyzer beat comparison/regression checks.
- `test_dmx_canvas_render.py`: DMX canvas rendering correctness checks.
- `test_ws_e2e.py`: WebSocket-level integration behavior.
- `live/`: manual or semi-manual live validation payloads.

## Run tests

Use the project Python environment (`ai-light`) and include repo + backend on `PYTHONPATH`:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q
```

Run a subset:

```bash
PYTHONPATH=.:./backend PYENV_VERSION=ai-light pyenv exec python -m pytest -q tests/test_ws_e2e.py
```

## Expected workflow

1. Run relevant tests for touched modules.
2. Run broader regression suite when behavior contracts change.
3. Rebuild/restart containers before manual validation:

```bash
docker compose down && docker compose up --build -d
```

## LLM contributor checklist

1. Prefer targeted tests first, then broaden scope.
2. Do not rewrite tests unrelated to the change.
3. If protocol/data contracts change, update tests in the same change.
4. Keep fixtures deterministic and avoid flaky timing assumptions.
