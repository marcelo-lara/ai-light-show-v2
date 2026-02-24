# Analyzer (song analysis) — Architecture

This document describes the `analyzer` module: the song analysis scripts, how they are run manually, and how results are integrated into the backend.

## Location

- Source: `analyzer/` (main script: `analyzer/analyze_song.py`)
- Output: `analyzer/meta/<song>/info.json` (canonical metadata file)
- Temporary working dir: `analyzer/temp_files/{song_slug}` (configurable via `ANALYZER_TEMP_DIR`).

## Purpose

- Extract deterministic metadata and derived artifacts for each song (stems, beatmaps, spectral features, run records).
- Produce reproducible JSON metadata under the configured meta directory (default: `analyzer/meta/{song_slug}`).

## API / CLI

- The pipeline is runnable via the local CLI: `python analyzer/analyze_song.py <song_path>`.
- For bulk runs the repository includes convenience scripts under `analyzer/`.

## Backend integration

- Backend reads metadata from `/app/meta` (mounted from `analyzer/meta` in Docker).
- If `/app/meta` is unavailable, backend falls back to local `backend/meta`.
- Backend accepts `info.json` as canonical, with fallback to legacy filenames like `<song>.json` or per-song directory formats.
- Metadata is loaded by `SongService` and exposed via WebSocket `initial` and `load_song` messages.

## Storage & outputs

- Output directory: by default `analyzer/meta/{song_slug}` (configurable via `out_dir`).
- Temporary working dir: `analyzer/temp_files/{song_slug}` (configurable via `ANALYZER_TEMP_DIR`).
- Run records and step artifact manifests are written into the song metadata directory (e.g., `run.json`).

## Docker & deployment notes

- The project `docker-compose.yml` includes an analyzer service for manual runs with GPU access.
- Environment variables used in analyzer scripts:
  - `ANALYZER_TEMP_DIR` (optional override)

## Testing & dev

- Unit tests and integration tests validate metadata loading and section save/dirty-state behavior.
- Tests no longer expect Celery task lifecycle messages; focus on manual metadata production + backend persistence on save.

## Troubleshooting

- Common issues:
  - Analyzer heavy models: long-running steps may need GPUs; use the analyzer image/runtime configured for `nvidia` if available.

## Required code changes for manual workflow

- Remove `analyze_song` message handling from `WebSocketManager.handle_message` in [backend/api/websocket.py](backend/api/websocket.py).
- Remove task lifecycle message handling (`task_submitted`, `analyze_progress`, `analyze_result`, `task_error`) from [frontend/src/app/state.jsx](frontend/src/app/state.jsx).
- Relabel/rewire "Start analysis" action to "Reload Metadata" in [frontend/src/pages/SongAnalysisPage.jsx](frontend/src/pages/SongAnalysisPage.jsx) to send `load_song` or similar reload message.

---
Reference: `analyzer/analyze_song.py`, `backend/store/state.py`, `backend/api/websocket.py`.

