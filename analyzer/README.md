# Analyzer Module (LLM Guide)

Offline song analysis pipeline that generates metadata consumed by backend playback and the backend-mounted MCP query surface.

## Purpose

- Generate beat/downbeat timing and musical descriptors.
- Produce per-song metadata under `analyzer/meta/<song>/`.
- Feed timing/feature truth to backend and its mounted MCP tools.
- Act as a standalone Docker service whose clients submit analyzer tasks and consume analyzer artifacts over stable service boundaries.

## Entry points

- `analyze_song.py`: orchestrates analyzer tasks from CLI/interactive flow.
- `src/api/`: HTTP request models and route registration for the analyzer service surface.
- `src/engines/`: low-level analysis implementations such as beat finding and stem splitting.
- `src/runtime/`: FastAPI app entrypoint, progress helpers, and worker lifecycle bootstrap for the analyzer container.
- `src/storage/`: song metadata paths and canonical analyzer file helpers.
- `src/engines/find_beats.py`: beat/downbeat extraction.
- `src/engines/split_stems.py`: Demucs-based stem extraction.
- `src/essentia_analysis/`: Essentia feature extraction and plotting helpers.
- `src/song_features/`: synthesizes LLM-facing song features from analyzer artifacts, beat-window stem accents, per-part relative dips, merged section-level low windows, optional music-model tags, and Essentia TensorFlow model outputs when that runtime is available.
- `src/musical_structure/`: Hugging Face-backed chord and section inference, comparison helpers, and model registry.
- `src/tasks/`: analyzer-owned single-purpose task modules used by the CLI, queue worker, and playlists.
- `src/report_tool/`: analyzer-owned report and summary generators such as beat comparison and markdown rendering.

## Service direction

- Treat the analyzer as a standalone Docker service, not as a backend-owned internal module.
- Backend is a client of the analyzer HTTP API, queue surface, and generated artifact contract.
- Favor analyzer-owned task metadata and filesystem contracts that can move to another repository without requiring cross-repo Python imports.
- Treat `moises/` as an external source of truth. Analyzer tasks may read and normalize Moises data into canonical analyzer outputs, but they must never overwrite or delete files inside `analyzer/meta/<song>/moises/`.

## Task dependencies and outcomes

| Task | Inputs | Outputs | Notes |
|---|---|---|---|
| `init-song` | source song path | `info.json` root | Creates only `song_name`, `song_path`, and `artifacts`.
| `split-stems` | source song path | `stems/*`, updated `info.json` | Initializes song metadata before writing derived fields.
| `beat-finder` | source song path, optional Moises files | `beats.json`, updated `info.json` | Imports Moises beats when usable chord data exists; otherwise runs analyzer beat detection.
| `import-moises` | `moises/chords.json` | `beats.json`, optional `sections.json` | Normalizes Moises beat rows and materializes sections from Moises segments when available, without modifying the original Moises files.
| `essentia-analysis` | source song path, optional stems | `essentia/*.json`, `essentia/*.svg`, `hints.json`, updated `info.json` | Builds section-indexed hints when sections exist; otherwise falls back to a single song-wide section.
| `find_chords` | `beats.json` | updated beats output, updated `info.json` | Optional beat enrichment step.
| `find_sections` | `beats.json` | `sections.json`, updated `info.json` | Produces canonical persisted song sections.
| `find-song-features` | `info.json`, `beats.json`, `essentia` mix artifacts | `features.json`, updated `info.json` | Also uses `sections.json` and `hints.json` when present.
| `generate-md` | `sections.json`, optional `features.json` | `<song>.md` | Terminal presentation artifact.

Recommended full-artifact order for analyzer-native songs: `init-song`, `split-stems`, `beat-finder`, `find-sections`, `essentia-analysis`, `find-song-features`, `generate-md`.

Recommended full-artifact order for Moises-backed songs: `init-song`, `split-stems`, `import-moises`, `essentia-analysis`, `find-song-features`, `generate-md`, with `find-sections` only when Moises segments are unavailable.

The executable full-artifact playlist lives in `src/playlists/full_artifact.py` and selects the analyzer-native or Moises-backed path from current song metadata.

## Progress callbacks

- Analyzer task wrappers in `analyze_song.py` accept an optional `progress_callback` parameter.
- `src/essentia_analysis/analyze_with_essentia.py` also accepts the same optional callback.
- The callback receives a dict containing `task_type`, `stage`, `step_current`, `step_total`, `message`, and optional `part_name`.
- These events report code-stage checkpoints only. They do not report frame counts, percentages, or other data-level progress metrics.
- Each `analyze_with_essentia(...)` call computes its own ordered stage list and restarts its `step_current/step_total` cycle for that specific part.

## Queue package

- Queue persistence lives at `analyzer/temp_files/queue.json`.
- Queue code lives in the dedicated `src/task_queue/` package.
- Public Python API is re-exported from `src/task_queue/__init__.py` and implemented in `src/task_queue/api.py`.
- The task catalog is analyzer-owned in `src/task_queue/dispatch.py`; each task entry includes `value`, `label`, and `description`.
- The queue catalog is sourced from analyzer task metadata in `src/tasks/catalog.py` rather than a hand-maintained dispatch branch table.
- The task catalog now includes `init-song`, which creates the canonical song metadata root before downstream tasks merge derived fields.
- Supported operations are `list_items(...)`, `add_item(...)`, `remove_item(...)`, `execute_item(...)`, and `process_queue(...)`.
- Queue item statuses are `queued`, `pending`, `running`, `complete`, and `failed`.
- `add_item(...)` stores task parameters and returns `item_id`.
  - If the same `task_type` and song (from `song_path`) are already queued/pending/running, it returns the existing `item_id` instead of adding a duplicate.
- `execute_item(item_id)` marks a queued item as `pending`.
- `process_queue(...)` runs the next pending item only when no item is currently marked `running`, persists the latest callback event in `progress`, and stores the final task result in `last_result`.
- Analyzer startup clears the persisted queue file before serving HTTP requests or running the worker loop.

## HTTP service

- The analyzer container serves `src/runtime/app.py` on port `8100`.
- The FastAPI app object and app factory live in `src/runtime/app.py`, and route registration lives in `src/api/routes.py`.
- The service exposes `GET /health`, `GET /task-types`, `GET /task-types/{task_type}`, `GET /queue/status`, `GET /queue/items`, `GET /queue/items/{item_id}`, `POST /queue/items`, `DELETE /queue/items/{item_id}`, `POST /queue/items/{item_id}/execute`, `POST /queue/playlists/full-artifact`, `POST /runtime/playback-lock`, `GET /playlists`, `GET /playlists/full-artifact`, `GET /playlists/full-artifact/metadata`, and `POST /playlists/full-artifact/execute`.
- `GET /task-types` returns the analyzer-owned task catalog used by backend validation and the Song Analysis queue UI.
- `GET /task-types/{task_type}` returns the full analyzer-owned schema for one task, including parameter descriptions, prerequisites, outputs, and notes.
- `GET /queue/status` returns the persisted queue items, a per-status summary, the current playback lock flag, and whether the in-process worker loop is active.
- The worker loop processes pending queue items only while playback lock is `false`.
- `POST /queue/playlists/full-artifact` enqueues the resolved playlist steps for one song and can mark them pending immediately so the worker loop can execute them without client-side per-task queue choreography.
- `GET /playlists` lists analyzer-owned playlist definitions.
- `GET /playlists/full-artifact` returns the resolved analyzer-native or Moises-backed task order for one song.
- `GET /playlists/full-artifact/metadata` returns the static playlist schema, parameters, variants, and produced artifacts without resolving a specific song.
- `POST /playlists/full-artifact/execute` runs that playlist synchronously through analyzer-owned task modules and returns the per-task results.
- Backend is the intended client for this service. It performs a one-shot status refresh at startup, stays idle while the queue is empty, and only polls continuously after queue activity is known. If status requests fail while the backend is already tracking queued or running analyzer work, it keeps retrying until `GET /queue/status` responds again. During show playback the backend stops polling and sets playback lock to `true`, so analyzer queue execution is paused until playback ends.

## Inputs and outputs

### Input sources

- Song files from `/app/songs` in Docker (mapped from `analyzer/songs`).

### Output structure

- `analyzer/meta/<song>/info.json`: canonical song metadata.
- `analyzer/meta/<song>/beats.json`: canonical mix beat events used by backend consumers. When `moises/` contains usable chord data, this file is normalized from `moises/chords.json`.
- `analyzer/meta/<song>/sections.json`: canonical persisted section list. When `moises/segments.json` exists and `sections.json` is absent, Moises import materializes this file using the analyzer section row shape (`start`, `end`, `label`, optional `description`, optional `hints`) after standalone section-range validation used by backend consumers.
- `analyzer/meta/<song>/hints.json`: section-indexed loudness hints, using the mix as the section anchor and stems as supporting evidence for significant local events.
- `analyzer/meta/<song>/features.json`: song-level and section-level feature metadata for light-show generation, including beat-aligned energy, phrase windows, dominant stems, harmonic motion, per-part relative dips, merged low windows, and optional semantic tags from a music audio-classification model.
- `analyzer/meta/<song>/essentia/*.json`: feature time series and descriptors.
- `analyzer/meta/<song>/essentia/*.svg`: optional plots.
- `analyzer/meta/<song>/stems/*`: separated stems when stem split is enabled.

Backend and MCP treat this folder as read-only input data.

## Run workflows

Use Docker so dependencies (Essentia/Demucs/toolchain) remain consistent.

### Start container

```bash
docker compose up analyzer --build
```

This starts the HTTP API on `http://localhost:8100` and the queue worker loop inside the analyzer container.

### Interactive mode

```bash
docker compose exec analyzer python analyze_song.py
```

Interactive option `8. Analyze All Songs` traverses every song in `/app/songs` and runs stem splitting, analyzer beat finding only when usable Moises chord data is absent, Essentia analysis, Moises import when available, and markdown generation for the resulting sections metadata.

Interactive option `4. Find Song Features` builds `features.json` for the selected song after beat and Essentia artifacts exist.

### CLI mode

```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --essentia-analysis --beat-finder
```

To run the executable full-artifact playlist for one song, run:

```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --full-artifact-playlist
```

To initialize the canonical song metadata root without running analysis, run:

```bash
docker compose exec analyzer python -m src.tasks.init_song "/app/songs/Armin - Revolution.mp3"
```

To validate chord inference against the canonical Yonaka beat metadata, run:

```bash
docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --find-chords --beats-output-name test.beats.json
```

To validate section inference against the canonical Yonaka section metadata, run:

```bash
docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --find-sections --sections-output-name test.sections.json
```

To validate Moises import and section/materialized metadata generation, run:

```bash
docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --import-moises
```

You can replace the song name with any other song that has usable `moises/` data.

To validate markdown generation from existing sections metadata, run:

```bash
docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --generate-md
```

You can replace the song name with any other song that already has usable `sections.json` data.

To validate feature synthesis from existing analyzer artifacts, run:

```bash
docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --find-song-features
```

### Common CLI flags

- `--song <filename>`: song in `/app/songs`.
- `--split-stems`: run Demucs separation.
- `--beat-finder`: run beat/downbeat extraction.
- `--essentia-analysis`: run Essentia analysis bundle.
- `--find-song-features`: synthesize LLM-facing feature metadata from analyzer outputs.
- `--find-chords`: run Hugging Face chord inference and write beat-aligned chord labels.
- `--find-sections`: run Hugging Face section inference and write `sections.json` rows.
- `--generate-md`: render the per-song markdown summary from `sections.json`.

Chord inference requires an existing `beats.json`. If it is missing, the analyzer warns and returns `None`. Bass inference uses `analyzer/temp_files/htdemucs/<song>/bass.wav` when present; if the bass stem is missing, the analyzer warns and keeps going with mix-only chord inference.

Section inference also requires an existing `beats.json`. If no section models are configured or all configured models fail, the analyzer warns and returns `None`.

Model retries are registry-driven. The analyzer tries the configured candidates in order and stops on the first successful model output. The default chord model is `andrewmcgill04/ast-finetuned-audioset-10-10-0.4593-chordy`. The default section model is `ArseniiChstiakovml/MusicSectionDetection`. Override or extend them through `ANALYZER_FIND_CHORDS_MODELS_JSON` and `ANALYZER_FIND_SECTIONS_MODELS_JSON`.

Every successful chord or section run also updates `info.json` with a `musical_structure_inference` object that records the selected method, confidence summary, candidate attempts, inputs, and output artifact path.

## Contract with other modules

- `backend/` loads metadata from `/app/meta` (mounted from `analyzer/meta`).
- The backend-mounted MCP tools read the same analyzer outputs for LLM-facing timing and structure queries.
- Do not emit schema-breaking changes in `info.json` or feature files without updating backend and MCP consumers in the same change.

## LLM contributor checklist

1. Keep output schema deterministic and JSON-serializable.
2. Prefer additive metadata fields; if breaking changes are required, update all consumers atomically.
3. Keep feature names and file naming stable across songs.
4. Validate with at least one real song end-to-end.

`info.json` groups Essentia artifacts by part first: `artifacts.essentia.mix.loudness_envelope`, `artifacts.essentia.bass.chroma_hpcp`, and so on. The derived loudness hints file is exposed separately as `artifacts.hints_file`.

`features.json` is additive and analyzer-owned. It records global energy, beat intensity, section-level energy/trend/phrase descriptors, dominant stems, harmonic-change counts, beat-window accents per part, per-part relative dips, merged low windows, semantic tags when the configured music model can run, and explicit attempt metadata for requested Essentia TensorFlow models. The analyzer image installs `essentia-tensorflow` and downloads the published `AudioSet-YAMNet`, `Nsynth instrument`, and `Discogs-EffNet` model assets into `/opt/essentia-models`; if the runtime still cannot execute them, the attempt metadata records the exact missing operator or file. Accents are stored with the beat anchor time plus the actual peak time inside that beat window, which lets markdown and downstream cue logic speak in bar/beat-aligned timestamps without losing the frame-level peak detail. Dips mark beat windows that fall below their neighboring bars, and low windows merge adjacent part dips into broader section-level ranges that read closer to how the music actually drops. Time fields are written at two-decimal precision for downstream prompt use. If a feature cannot be identified, the analyzer logs that condition and leaves the corresponding metadata unavailable instead of inventing substitute values.

`hints.json` is a plain list of song sections. Each section includes its time window and a `hints` array containing relevant `rise`, `drop`, `sustain`, and `sudden_spike` entries. Mix drives section-level meaning, while stems only appear when they materially support a local event.

Stem Essentia files use a consistent `<part>_<feature>.json` and `<part>_<feature>.svg` naming pattern in the song `essentia` directory, while the mix keeps unprefixed filenames like `loudness_envelope.json` and `rhythm.json`.


## Verification

```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --essentia-analysis
```
```bash
docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --find-song-features
```
```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --split-stems
```
```bash
docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --import-moises
```
```bash
docker compose exec analyzer python analyze_song.py --song "Yonaka - Seize the Power.mp3" --generate-md
```

Then verify output artifacts exist in `analyzer/meta/<song>/` and are readable JSON.

## Appendix

### Beats.json file

`beats.json` is an array of beat events:

```json
[
	{
		"time": 0.0,
		"beat": 2,
		"bar": 0,
		"bass": null,
		"chord": null,
		"type": "beat"
	}
]
```

Event fields:

- `time` (number): beat timestamp in seconds (float precision of 3 digits. Example: 1.234).
- `bar` (integer): bar index, incremented on each downbeat.
- `beat` (integer): beat index within the current bar from the canonical beat source.
- `bass` (string | null): inferred bass note label, or `null` when unavailable.
- `chord` (string | null): inferred chord label for the mix (for example `Fm`, `C#`, `N`).
- `type` (string): `downbeat` when `beat == 1`, otherwise `beat`.

## Backlog

- Upgrade the analyzer image to include the CUDA/CuDNN stack expected by the TensorFlow build so Essentia model inference can use the GPU too.