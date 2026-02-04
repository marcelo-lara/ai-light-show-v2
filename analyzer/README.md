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

The analyzer processes a song through 9 phases to create comprehensive musical analysis artifacts:
- Stem separation (drums / bass / vocals / other) so you can drive different fixtures from different musical roles.
- Beat grid + tempo curve (beats and downbeats)
- Onsets (kick/snare/hihat hits; synth stabs)
- Section boundaries (intro / verse / chorus / breakdown)
- Energy curve (overall loudness + perceived intensity)
- Spectral descriptors (brightness, bass energy, noisiness)
- Vocal activity / phrase timing (so the moving head “sings” when the singer sings).
- Chord/harmony roughness (for color palette shifts), if you want “music theory aware” looks.

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

The analyzer is runnable as a CLI on a headless Linux server (NVIDIA GPU available):

```bash
python -m song_analyzer analyze songs/<song>.mp3
```

Implemented flags:

- `--device auto|cuda|cpu`
- `--out metadata/`
- `--temp temp_files/`
- `--stems-model demucs:<model_name>`
- `--overwrite`
- `--until <step>` (for incremental development)

## output metadata definition

The analyzer writes one output directory per song under `analyzer/metadata/<song_slug>/`.

Example:

```
analyzer/metadata/
└── sono_keep_control/
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
  ├── show_plan/
  │   ├── roles.json
  │   ├── moments.json
  │   └── show_plan.json      # contract (index)
  └── README.md
```

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

- use the "ai-light" python environment.
- update "requirements.txt" as needed
- DO NOT use fallbacks, if a model fails, log a warning, but never simple calculations.
- this is a NEW PoC project: don't add backward compatibility, breaking changes are allowed.
- update this document for future LLMs.

## GPU Usage

This project can run analysis on machines with an NVIDIA GPU for much faster stem separation (Demucs) and other ML steps.

Quick `docker run` example that mounts the songs and metadata folders and exposes the GPU to the container:

```bash
docker run --rm --gpus all \
  -v $(pwd)/backend/songs:/input_songs \
  -v $(pwd)/backend/metadata:/app/metadata \
  -v $(pwd)/analyzer/temp_files:/app/temp_files \
  ai-light-show-v2-analyzer \
  analyze "/input_songs/sono - keep control.mp3" --device cuda --out metadata/sono_keep_control --temp temp_files --overwrite
```

Compose note: the `analyzer` service in `docker-compose.yml` is configured to use the NVIDIA runtime (`runtime: nvidia`). If your environment prefers Compose-native device requests and your Compose version supports `device_requests`, replace the runtime entry with a `device_requests` block.

Verify GPU availability on the host with `nvidia-smi` before running.

## Notes on model selection

This project intentionally prefers modern ML-first approaches (GPU when useful). The current recommended shortlist and per-phase model choices are documented in `implementation_backlog.md`.