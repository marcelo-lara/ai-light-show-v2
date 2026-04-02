# Analyzer (song analysis) — Architecture

This document describes the analyzer service, its task execution model, and the artifact contract consumed by backend playback and backend-mounted MCP tools.

## Location

- Source root: `analyzer/`
- CLI entrypoint: `analyzer/analyze_song.py`
- HTTP entrypoint: `analyzer/src/runtime/app.py`
- Canonical outputs: `analyzer/meta/<song>/...`
- Queue persistence: `analyzer/temp_files/queue.json`

## Purpose

- Generate deterministic song-analysis artifacts such as metadata roots, stems, beats, sections, Essentia descriptors, hints, features, and markdown summaries.
- Execute analyzer-owned tasks through either the CLI flow or the analyzer HTTP queue and playlist surfaces.
- Present the analyzer as a standalone Docker service that backend calls over HTTP instead of through Python imports.

## Module layout

- `src/api/`: request models and FastAPI route registration.
- `src/runtime/`: ASGI app entrypoint, worker lifecycle, and progress helpers.
- `src/storage/`: canonical song metadata path and JSON helpers.
- `src/engines/`: low-level analysis implementations such as beat finding and stem splitting.
- `src/tasks/`: analyzer-owned single-purpose task modules with metadata used by CLI, queue, and playlists.
- `src/task_queue/`: persisted queue operations and queue worker dispatch.
- `src/playlists/`: analyzer-owned ordered task plans such as the full-artifact playlist.
- `src/report_tool/`: report generation helpers such as markdown rendering and beat comparison.

## Service model

- The analyzer container serves `src.runtime.app:app` on port `8100`.
- The FastAPI lifespan owns queue-path resolution, playback lock state, queue startup clearing, and the background worker loop.
- The worker loop only processes pending items while playback lock is `false`.
- Backend is the intended client. It reads analyzer task metadata, queue state, and playlist resolution over HTTP and loads generated files from `/app/meta`.
- `moises/` under `analyzer/meta/<song>/` is external source-of-truth input. Analyzer may normalize it into canonical outputs but must never overwrite or delete those source files.

## Task and playlist flow

- `src/tasks/catalog.py` is the analyzer-owned source of truth for task ids, labels, parameter schemas, prerequisites, outputs, and execution functions.
- Queue dispatch resolves tasks from that metadata instead of a hand-maintained branch table.
- The full-artifact playlist lives in `src/playlists/full_artifact.py`.
- Full-artifact execution selects the analyzer-native or Moises-backed task order from the current song metadata directory.
- Recommended analyzer-native order: `init-song`, `split-stems`, `beat-finder`, `find-sections`, `essentia-analysis`, `find-song-features`, `generate-md`.
- Recommended Moises-backed order: `init-song`, `split-stems`, `import-moises`, `essentia-analysis`, `find-song-features`, `generate-md`, with `find-sections` only when Moises segments are unavailable.

## Artifact contract

- `info.json`: canonical song metadata root with analyzer-owned artifact references.
- `beats.json`: canonical beat events used by backend and MCP consumers.
- `sections.json`: canonical persisted section rows.
- `hints.json`: section-indexed loudness hints derived from mix and supporting stem evidence.
- `features.json`: analyzer-owned song and section feature summary for light-show generation.
- `essentia/*.json` and `essentia/*.svg`: feature time series, descriptors, and optional plots.
- `stems/*`: Demucs outputs when stem splitting is requested.

## CLI and HTTP surfaces

- CLI orchestration remains in `analyze_song.py` for manual runs and direct task execution.
- The HTTP service exposes health, task catalog, queue, playback-lock, and playlist endpoints.
- `POST /queue/playlists/full-artifact` schedules the resolved playlist steps for one song.
- `POST /playlists/full-artifact/execute` runs the resolved playlist synchronously and returns per-task results.

## Backend integration

- Backend loads analyzer artifacts from `/app/meta` during song load and relays analyzer queue state under `state.analyzer`.
- During playback, backend stops analyzer polling and keeps analyzer playback lock enabled so queue execution pauses.
- Analyzer startup clears persisted queue items before serving requests, so backend observes an empty queue after analyzer restarts.

## Validation

- Start the analyzer container with `docker compose up analyzer --build`.
- Run the analyzer-local HTTP and playlist regression suite with `PYTHONPATH=. PYENV_VERSION=ai-light pyenv exec python -m pytest analyzer/tests/test_init_song.py analyzer/tests/test_task_dispatch.py analyzer/tests/test_full_artifact_playlist.py analyzer/tests/test_http_api.py`.
- For manual validation, run `docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --full-artifact-playlist`.

---
Reference: `analyzer/analyze_song.py`, `analyzer/src/runtime/app.py`, `analyzer/src/tasks/catalog.py`, `analyzer/src/playlists/full_artifact.py`.
