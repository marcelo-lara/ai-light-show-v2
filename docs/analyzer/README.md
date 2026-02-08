# Song Analyzer

This service receives an mp3 song to analyze using AI/ML tools, then create a intermediate representation (IR) for later use by LLMs.

## Implementation status

The build plan (phased backlog + JSON contracts + proposed module layout) lives in:

- `implementation_backlog.md`

This README describes the desired behavior and output layout. The actual implementation should follow the backlog phases and ship incrementally.

## Current Implementation

- ✅ **Phase 0**: Project scaffolding + ingestion (foundation) - MP3 decode to WAV, metadata extraction
- ✅ **Phase 1**: Stem separation using Demucs v4 (GPU-first)
- ✅ **Phase 2**: Beat grid + tempo curve using librosa
- ✅ **Phase 3**: Energy curves (per stem + overall) using librosa
- ✅ **Phase 4**: Drum event extraction (kick/snare/hihat) using librosa onset strength
- ✅ **Phase 5**: Vocal activity detection using librosa
- ✅ **Phase 6**: Song section analysis using OpenL3 embeddings
- ✅ **Phase 7**: Drum pattern mining using DBSCAN clustering
- ✅ **Phase 8**: Show plan IR generation for LLM consumption

## High Level Flow

The analyzer processes a song through a fixed sequence of steps to create analysis artifacts (JSON) and visualization artifacts (SVG plots):
- Stem separation (drums / bass / vocals / other) so you can drive different fixtures from different musical roles.
- Beat grid + tempo curve (beats and downbeats)
- Onsets (kick/snare/hihat hits; synth stabs)
- Section boundaries (intro / verse / chorus / breakdown)
- Energy curve (overall loudness + perceived intensity)
- Spectral descriptors (brightness, bass energy, noisiness)
- Vocal activity / phrase timing (so the moving head “sings” when the singer sings).
- Chord/harmony roughness (for color palette shifts), if you want “music theory aware” looks.

Additionally:
- A show-plan IR is generated under `show_plan/` (roles + notable moments + an index).
- Step 100 generates SVG waveform plots under `analysis/plots/`.

2) Convert signals → an intermediate “Show Plan” (don’t jump straight to DMX)

Create an intermediate representation (IR) like:
- beats[]: timestamps, downbeats, bars
- sections[]: (start, end, label, confidence)
- tracks[]: drums/bass/vocals energy over time
- events[]: kick hits, snare hits, vocal phrases, big risers, drops

- extract song stems: drums, bass, voice and other wav files. these files should be stored in "temp_files"
- extract the time of drum parts: kick, snare and hi-hat.
- identify the song patterns: repeating kick and snare patterns, a list of this patterns and a list whrere these patterns starts.
- identify segments of the energy of the voice track, creating a precise timeline with of each change (also consider the time window of the silence).

## CLI (implemented)

The analyzer is runnable as a CLI on a headless Linux server (NVIDIA GPU available).

The Docker image sets the entrypoint to `python -m song_analyzer.cli`.

```bash
python -m song_analyzer.cli analyze songs/<song>.mp3
```

Implemented flags:

- `--device auto|cuda|cpu`
- `--out metadata/`
- `--temp temp_files/`
- `--stems-model <model_name>` (default: `htdemucs_ft`)
- `--overwrite`
- `--until <step>` (for incremental development)

## Device Configuration

The analyzer supports GPU acceleration when possible. Use the `--device` flag to control hardware usage:

- `--device auto`: Automatically detect and use GPU if available, fallback to CPU
- `--device cuda`: Force GPU usage (fails if no GPU available)
- `--device cpu`: Force CPU usage

GPU usage is recommended for faster processing, especially for stem separation and ML-based analysis steps.

## output metadata definition

The analyzer writes one output directory per song under `<metadata_dir>/<song_slug>/`.

- In Docker Compose, `metadata_dir` is mounted at `/app/metadata` from `./backend/metadata`.
- Temporary files are written under `<temp_dir>/<song_slug>/`.

Example:

```
<metadata_dir>/
└── <song_slug>/
  ├── analysis/
  │   ├── run.json
  │   ├── timeline.json
  │   ├── stems.json
  │   ├── beats.json
  │   ├── energy.json
  │   ├── onsets.json
  │   ├── vocals.json
  │   ├── sections.json
  │   └── patterns.json
  ├── plots/
  │   ├── beats.svg
  │   ├── energy.svg
  │   ├── sections.svg
  │   ├── vocals.svg
  │   ├── drums.svg
  │   ├── bass.svg
  │   └── other.svg
  └── show_plan/
      ├── roles.json
      ├── moments.json
      └── show_plan.json      # index contract
```

Notes:
- Stems WAVs are written to `<temp_dir>/<song_slug>/stems/{drums,bass,vocals,other}.wav`.
- The plots are written into metadata (not temp) so the backend service can read them via the `backend/metadata` volume.

For incremental development, see the “Phase artifacts checklist” in `implementation_backlog.md`.

### show_plan.json contract

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-02-03T21:51:38.000Z",
  "includes": {
    "timeline": "../analysis/timeline.json",
    "stems": "../analysis/stems.json",
    "beats": "../analysis/beats.json",
    "energy": "../analysis/energy.json",
    "onsets": "../analysis/onsets.json",
    "vocals": "../analysis/vocals.json",
    "sections": "../analysis/sections.json",
    "patterns": "../analysis/patterns.json",
    "roles": "./roles.json",
    "moments": "./moments.json"
  },
  "meta": {
    "style": "electronic_vocal",
    "llm_version": "unknown",
    "confidence": 0.0,
    "notes": "Show plan generated from available analysis artifacts"
  }
}
```

## LLM Developer Instructions

- Use the "ai-light" python environment.
- Update `requirements.txt` as needed.
- This is a PoC project: avoid backward-compatibility shims; breaking changes are acceptable.
- The current implementation includes a few fallbacks (e.g., sections extraction if OpenL3 is unavailable or fails, and an energy-based fallback if VAD returns no segments). When a fallback is used, it should be surfaced via logs and/or artifact metadata.
- Keep this document aligned with the actual code and folder layout.

## GPU Usage

This project can run analysis on machines with an NVIDIA GPU for much faster stem separation (Demucs) and other ML steps.

Quick `docker run` example that mounts the songs and metadata folders and exposes the GPU to the container:

```bash
docker run --rm --gpus all \
  -v $(pwd)/backend/songs:/app/songs \
  -v $(pwd)/backend/metadata:/app/metadata \
  -v $(pwd)/analyzer/temp_files:/app/temp_files \
  ai-light-show-v2-analyzer \
  analyze "/app/songs/sono - keep control.mp3" --device cuda --out /app/metadata --temp /app/temp_files --overwrite
```

To analyze all songs in the songs folder:

```bash
docker run --rm --gpus all \
  -v $(pwd)/backend/songs:/app/songs \
  -v $(pwd)/backend/metadata:/app/metadata \
  -v $(pwd)/analyzer/temp_files:/app/temp_files \
  ai-light-show-v2-analyzer \
  analyze-all /app/songs --device cuda --out /app/metadata --temp /app/temp_files --overwrite
```

Compose note: the `analyzer` service in `docker-compose.yml` is configured to use the NVIDIA runtime (`runtime: nvidia`). If your environment prefers Compose-native device requests and your Compose version supports `device_requests`, replace the runtime entry with a `device_requests` block.

Verify GPU availability on the host with `nvidia-smi` before running.

## Notes on model selection

This project intentionally prefers modern ML-first approaches (GPU when useful). The current recommended shortlist and per-phase model choices are documented in `implementation_backlog.md`.

## Docker Compose filesystem layout (canonical)

When running via `docker compose`, these are the important in-container paths:

- Songs (MP3 inputs): `/app/songs/*.mp3` (mounted from `./backend/songs`)
- Metadata outputs: `/app/metadata/<song_slug>/...` (mounted from `./backend/metadata`)
- Temp files (decoded WAV + stems): `/app/temp_files/<song_slug>/...` (mounted from `./analyzer/temp_files`)

Step 100 writes SVGs to `/app/metadata/<song_slug>/plots/*.svg` and reads stems from `/app/temp_files/<song_slug>/stems/*.wav`.