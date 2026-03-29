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
- To validate Moises import in the container, run `docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --import-moises` or replace the song name with another track that has usable `moises/` data.
- To validate markdown generation in the container, run `docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --generate-md` or replace the song name with another track that already has usable `sections.json` data.
- For bulk runs the repository includes convenience scripts under `analyzer/`.

## Backend integration

- Backend reads metadata from `/app/meta` (mounted from `analyzer/meta` in Docker).
- If `/app/meta` is unavailable, backend falls back to local `backend/meta`.
- Backend accepts `info.json` as canonical, with fallback to legacy filenames like `<song>.json` or per-song directory formats.
- Metadata is loaded during song load in `StateManager` and exposed through websocket `snapshot` / `patch` state payloads.

## Storage & outputs

- Output directory: by default `analyzer/meta/{song_slug}` (configurable via `out_dir`).
- Temporary working dir: `analyzer/temp_files/{song_slug}` (configurable via `ANALYZER_TEMP_DIR`).
- Run records and step artifact manifests are written into the song metadata directory (e.g., `run.json`).
- `info.json` stores Essentia artifacts grouped by part under `artifacts.essentia.{mix|bass|drums|vocals|other}.{feature}`.
- `sections.json` is the canonical persisted top-level list of section rows. Rows use analyzer-authored fields like `start`, `end`, and `label`, and may also carry `description` and `hints` on the same objects.
- `hints.json` stores a plain list of song sections with relevant loudness-shape hints. Mix anchors section-level meaning, and stem events are folded in only when they materially support a local `rise`, `drop`, or `sudden_spike`. Stable high-energy sections receive `sustain` hints. The file is referenced by `artifacts.hints_file`.
- Moises data (`moises/` directory): Exists purely for internal importing or beat-sync comparison purposes within the analyzer module and should never be used as a system-wide source of truth by the UI, Backend, or external systems (like MCP). The unified source of truth for rhythm data output is `analyzer/meta/{song_slug}/beats.json`. When `moises/segments.json` is present and `sections.json` is missing, the analyzer may materialize `sections.json` from those segments, but only after standalone section validation that stays compatible with backend section consumers.

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

---
Reference: `analyzer/analyze_song.py`, `backend/store/state.py`, `backend/api/websocket_manager/messaging.py`.
