# Analyzer (song analysis) — Architecture

This document describes the `analyzer` module: the song analysis pipeline, how it is invoked, and how progress/results are integrated into the backend.

## Location

- Source: `analyzer/` (main pipeline: `analyzer/song_analyzer/pipeline.py`)
- CLI: `analyzer/implementation_backlog.md` and the `analyzer` image used for heavy GPU runs (optional)

## Purpose

- Extract deterministic metadata and derived artifacts for each song (stems, beatmaps, spectral features, run records).
- Produce reproducible JSON metadata under the configured metadata directory (default: `backend/metadata/{song_slug}`).

## API / CLI

- The pipeline is runnable via the local CLI image or directly as Python: `AnalysisPipeline.analyze_song(song_path, progress_callback=...)`.
- For bulk runs the repository includes a convenience entrypoint used in CI and Docker builds (see `analyzer/` top-level README).

## Backend integration

- Celery task: `backend/tasks/analyze.py` exposes a Celery task `analyze_song` which:
  - Lazily imports `analyzer.song_analyzer` internals.
  - Constructs `AnalysisConfig` with `songs_dir`, `metadata_dir`, `temp_dir`, and `device`.
  - Calls `pipeline.analyze_song(song_path, progress_callback=_progress_cb)`.

- WebSocket flow: `backend/api/websocket.py` listens for messages `{type: "analyze_song", filename: ...}` and:
  - Validates song file presence under the `SongService` path.
  - Submits `analyze_task.apply_async(...)` to Celery and returns `{type: "task_submitted", task_id}` to the client.
  - Starts `_track_task_progress(task_id)` background coroutine to poll Celery task meta and broadcast progress messages.

## Progress reporting

- Two mechanisms are used by the Celery task to report progress:
  1. `self.update_state(state='PROGRESS', meta={...})` — Celery task meta (polled by the backend via `AsyncResult`).
  2. Redis pub/sub (optional) — task publishes JSON messages to channel `analyze:{task_id}` when a Redis client is available.

- The progress meta includes fields: `progress` (percent), `step` (step name), `status`, `index`, `total`.

- The WebSocket manager broadcasts `{type: 'analyze_progress', task_id, state, meta}` and final `{type: 'analyze_result', task_id, state, result}` to connected clients.

## Storage & outputs

- Output directory: by default `backend/metadata/{song_slug}` (configurable via `out_dir` or `ANALYZER_METADATA_DIR`).
- Temporary working dir: `analyzer/temp_files/{song_slug}` (configurable via `ANALYZER_TEMP_DIR`).
- Run records and step artifact manifests are written into the song metadata directory (e.g., `run.json`).

## Docker & deployment notes

- The project `docker-compose.yml` includes a `worker` service that runs the Celery worker and mounts `./analyzer` and song/metadata dirs.
- Environment variables used in the worker/backend:
  - `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (default: `redis://redis:6379/0`)
  - `ANALYZER_METADATA_DIR` (optional override)
  - `ANALYZER_TEMP_DIR` (optional override)
  - `CELERY_IMPORTS` may be set to ensure the worker imports `tasks.analyze` on startup.

## Testing & dev

- Unit tests and integration tests use two approaches:
  - Fast unit tests mock the analyzer and run the Celery task with `task_always_eager=True` so no Redis/Celery worker is required.
  - Optional real E2E tests spin up Redis + a local Celery worker (controlled with `REAL_E2E=1`) and assert progress messages are delivered over the WebSocket manager.

## Troubleshooting

- Common issues:
  - Task not registered: ensure worker process sets `PYTHONPATH=/app` and `CELERY_IMPORTS` includes `tasks.analyze`.
  - Redis unreachable: verify `redis` service in `docker-compose` or host `REDIS_HOST/REDIS_PORT` when running tests from host.
  - Analyzer heavy models: long-running steps may need GPUs; use the analyzer image/runtime configured for `nvidia` if available.

## Recommended usage

- For local development use the `ai-light` Python environment and run tests with `PYTHONPATH=./backend` to import backend packages. Use eager mode for fast iterations.
- For full analysis runs use the containerized worker with GPU access where required; ensure `metadata` and `temp_files` are persisted to host volume for inspection.

---
Reference: `backend/tasks/analyze.py`, `backend/tasks/celery_app.py`, `backend/api/websocket.py`, `analyzer/song_analyzer/pipeline.py`, `docs/analyzer/README.md`.

