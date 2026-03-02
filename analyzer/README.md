# Analyzer Module (LLM Guide)

Offline song analysis pipeline that generates metadata consumed by backend playback and MCP query services.

## Purpose

- Generate beat/downbeat timing and musical descriptors.
- Produce per-song metadata under `analyzer/meta/<song>/`.
- Feed timing/feature truth to backend and `mcp/song_metadata`.

## Entry points

- `analyze_song.py`: orchestrates analyzer tasks from CLI/interactive flow.
- `src/beat_finder.py`: beat/downbeat extraction.
- `src/split_stems.py`: Demucs-based stem extraction.
- `src/essentia_analysis/`: Essentia feature extraction and plotting helpers.

## Inputs and outputs

### Input sources

- Song files from `/app/songs` in Docker (mapped from `backend/songs`).

### Output structure

- `analyzer/meta/<song>/info.json`: canonical song metadata.
- `analyzer/meta/<song>/beats.json`: analyzer beat/downbeat times.
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

### Interactive mode

```bash
docker compose exec analyzer python analyze_song.py
```

### CLI mode

```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --essentia-analysis --beat-finder
```

### Common CLI flags

- `--song <filename>`: song in `/app/songs`.
- `--split-stems`: run Demucs separation.
- `--beat-finder`: run beat/downbeat extraction.
- `--essentia-analysis`: run Essentia analysis bundle.

## Contract with other modules

- `backend/` loads metadata from `/app/meta` (mounted from `analyzer/meta`).
- `mcp/song_metadata/` indexes analyzer outputs for tool queries.
- Do not emit schema-breaking changes in `info.json` or feature files without updating backend + MCP consumers in the same change.

## LLM contributor checklist

1. Keep output schema deterministic and JSON-serializable.
2. Prefer additive metadata fields; if breaking changes are required, update all consumers atomically.
3. Keep feature names and file naming stable across songs.
4. Validate with at least one real song end-to-end.

## Verification

```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --essentia-analysis
```

Then verify output artifacts exist in `analyzer/meta/<song>/` and are readable JSON.