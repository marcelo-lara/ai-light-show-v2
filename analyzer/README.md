# Analyzer Module (LLM Guide)

Offline song analysis pipeline that generates metadata consumed by backend playback and the backend-mounted MCP query surface.

## Purpose

- Generate beat/downbeat timing and musical descriptors.
- Produce per-song metadata under `analyzer/meta/<song>/`.
- Feed timing/feature truth to backend and its mounted MCP tools.

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
- `analyzer/meta/<song>/beats.json`: canonical mix beat events used by backend consumers. When `moises/` contains usable chord data, this file is normalized from `moises/chords.json`.
- `analyzer/meta/<song>/hints.json`: section-indexed loudness hints, using the mix as the section anchor and stems as supporting evidence for significant local events.
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

Interactive option `8. Analyze All Songs` traverses every song in `/app/songs` and runs stem splitting, analyzer beat finding only when usable Moises chord data is absent, Essentia analysis, and Moises import when available.

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
- The backend-mounted MCP tools read the same analyzer outputs for LLM-facing timing and structure queries.
- Do not emit schema-breaking changes in `info.json` or feature files without updating backend and MCP consumers in the same change.

## LLM contributor checklist

1. Keep output schema deterministic and JSON-serializable.
2. Prefer additive metadata fields; if breaking changes are required, update all consumers atomically.
3. Keep feature names and file naming stable across songs.
4. Validate with at least one real song end-to-end.

`info.json` groups Essentia artifacts by part first: `artifacts.essentia.mix.loudness_envelope`, `artifacts.essentia.bass.chroma_hpcp`, and so on. The derived loudness hints file is exposed separately as `artifacts.hints_file`.

`hints.json` is a plain list of song sections. Each section includes its time window and a `hints` array containing relevant `rise`, `drop`, `sustain`, and `sudden_spike` entries. Mix drives section-level meaning, while stems only appear when they materially support a local event.

Stem Essentia files use a consistent `<part>_<feature>.json` and `<part>_<feature>.svg` naming pattern in the song `essentia` directory, while the mix keeps unprefixed filenames like `loudness_envelope.json` and `rhythm.json`.


## Verification

```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --essentia-analysis
```
```bash
docker compose exec analyzer python analyze_song.py --song "Armin - Revolution.mp3" --split-stems
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
