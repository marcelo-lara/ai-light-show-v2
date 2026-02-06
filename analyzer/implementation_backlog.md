# Analyzer Implementation Backlog (PoC)

**Scope**: Everything in this plan lives under `/analyzer` only.

**Goal**: Take an MP3 from `analyzer/songs/`, run ML-first audio analysis on a Linux headless NVIDIA GPU server, and emit an LLM-friendly Intermediate Representation (IR) under `analyzer/metadata/<song_slug>/`.

**Non-goals (for now)**
- No DMX generation here (that belongs elsewhere).
- No web service/API until the pipeline is stable.

**Hard requirements**
- Prefer *latest* practical ML models (GPU when helpful).
- No “fallback math” if a model fails. If a model step fails: **log a warning and omit that artifact** (leave a structured failure record).
- Pythonic layout: small modules, clear types, reproducible outputs.

**Copilot guardrails (important)**
- Implement exactly one primary model/backend per phase (pin it and move on). Do not add multiple backends “just in case”.
- If an ML step fails, do not replace it with heuristic DSP or hand-rolled approximations. Record the failure and continue.
- Keep outputs stable and diff-friendly (deterministic ordering, consistent float formatting).

---

## Proposed repo layout (inside `/analyzer`)

Create a real Python package so the pipeline is testable and composable:

```
/analyzer/
  song_analyzer/
    __init__.py
    cli.py
    pipeline.py
    config.py
    logging.py
    io/
      audio_decode.py
      paths.py
      json_write.py
      hashing.py
    models/
      schemas.py              # dataclasses/pydantic models for JSON output
      failures.py
    steps/
      step_00_ingest.py
      step_10_stems.py
      step_20_beats.py
      step_30_energy.py
      step_40_drums.py
      step_50_vocals.py
      step_60_sections.py
      step_70_patterns.py
      step_80_show_plan.py
    ml/
      demucs.py
      beat_tracker.py
      drum_transcription.py
      embeddings.py
      vad.py
  requirements.txt
  implementation_backlog.md
  README.md
  songs/
  temp_files/
  metadata/
```

Design rule: each `steps/step_xx_*.py` exports one function:

- `run(ctx: AnalysisContext) -> StepResult`

Where `ctx` knows input/output paths + config, and `StepResult` carries:

- `artifacts_written: list[path]`
- `warnings: list[str]`
- `failure: Optional[FailureRecord]`

---

## Execution model

### CLI
Implement a single CLI command:

- `python -m song_analyzer analyze songs/<file>.mp3`

Flags:
- `--out metadata/` (default)
- `--temp temp_files/` (default)
- `--device cuda|cpu|auto` (default `auto`)
- `--stems-model demucs:<model_name>`
- `--overwrite` (safe, explicit)

Recommended library: `typer` (simple, Pythonic), or stdlib `argparse`.

### Golden commands (must keep working as the project evolves)

These commands define the minimum UX contract Copilot should preserve across phases:

1) Analyze all implemented phases
- `python -m song_analyzer analyze songs/<song>.mp3`

2) Analyze up to a specific phase (for incremental development)
- `python -m song_analyzer analyze songs/<song>.mp3 --until stems`
- `python -m song_analyzer analyze songs/<song>.mp3 --until beats`

3) Re-run a single phase (debugging)
- `python -m song_analyzer run-step stems songs/<song>.mp3`

Expected result: artifacts appear under `metadata/<song_slug>/analysis` and `metadata/<song_slug>/show_plan` with `analysis/run.json` updated.

### Output directory naming
Use a stable `song_slug`:
- normalize filename (lowercase)
- replace spaces with `_`
- strip extension

Example:
- `sono - keep control.mp3` → `sono_keep_control`

Outputs:
```
metadata/sono_keep_control/
  analysis/
  show_plan/
  README.md
```

---

## Backlog phases (build incrementally)

Each phase should ship working code + JSON outputs + one focused test.

### Phase artifacts checklist (LLM-friendly “definition of done”)

| Phase | Step name | Required inputs | Required outputs | Optional outputs |
|------:|-----------|-----------------|------------------|------------------|
| 0 | ingest | songs/<song>.mp3 | analysis/timeline.json, analysis/run.json, temp_files/<slug>/audio/source.wav | temp_files/<slug>/run_<timestamp>.log |
| 1 | stems | analysis/timeline.json, source.wav | analysis/stems.json, temp_files/<slug>/stems/*.wav | - |
| 2 | beats | stems.json (or source.wav) | analysis/beats.json | - |
| 3 | energy | timeline.json, stems (if available) | analysis/energy.json | energy curves per-stem |
| 4 | drums | stems: drums.wav, beats.json | analysis/onsets.json | - |
| 5 | vocals | stems: vocals.wav | analysis/vocals.json | phrases[] |
| 6 | sections | embeddings source (mix or stems) | analysis/sections.json | novelty curve debug JSON |
| 7 | patterns | beats.json, onsets.json | show_plan/patterns.json | - |
| 8 | show_plan | analysis/* (as available) | show_plan/show_plan.json, show_plan/roles.json, show_plan/moments.json | show_plan/README.md |
| 9 | plot_analysis_results | analysis/*.json, temp_files/<slug>/audio/source.wav | analysis/plots/beats.png, analysis/plots/energy.png, analysis/plots/sections.png, analysis/plots/vocals.png | - |

### Phase 0 — Project scaffolding + ingestion (foundation)
**Deliverable**: deterministic pipeline skeleton that runs end-to-end and writes `analysis/timeline.json`.

Tasks
- Convert `analyzer/main.py` (currently notebook-style) into a minimal CLI wrapper (or replace it entirely with `song_analyzer/cli.py`).
- Add structured logging (`logging` module) + one log file per run.
- Add consistent JSON writer:
  - pretty, stable key ordering
  - UTF-8
  - floats rounded to a fixed precision for diffs (e.g., 6 decimals)
- Add MP3 decode to WAV (mono+stereo options):
  - prefer `ffmpeg` via `ffmpeg-python` or direct subprocess invocation
  - write `temp_files/<song_slug>/audio/source.wav`
- Collect timeline metadata:
  - duration seconds
  - sample rate
  - channels

Suggested deps
- `pydantic` (or `pydantic-settings`) for config + schema validation
- `typer` for CLI
- `soundfile` + `ffmpeg-python` (or keep pure `ffmpeg` subprocess)

Artifacts
- `analysis/timeline.json`
- `analysis/run.json` (captures versions + failures)

Test
- Decode a short fixture MP3 (or a generated sine) and assert duration/sample rate fields exist.

---

### Phase 1 — Stem separation (GPU-first)
**Deliverable**: replace Spleeter usage with a modern separator and emit `analysis/stems.json` + WAV stems.

Model recommendation (latest practical)
- **Demucs v4** (PyTorch; excellent quality; uses GPU well)
  - model candidates: `htdemucs`, `htdemucs_ft`, `mdx_extra` (choose based on quality/speed)

Implementation notes
- Write stems to:
  - `temp_files/<song_slug>/stems/<stem>.wav` for: `drums`, `bass`, `vocals`, `other`
- Record:
  - model name + version
  - device used (cuda/cpu)
  - runtime

Failure rule
- If stem model fails: log warning, write `analysis/stems.json` with `status:"failed"` and a `failure` record; do not attempt a different separator.

Test
- Given a short WAV input, ensure four stem files are created and readable.

---

### Phase 2 — Beat grid + tempo curve (beat/downbeat)
**Deliverable**: `analysis/beats.json` with beats, downbeats, tempo curve.

Model options (pick one; don’t implement multiple in v1)
- **madmom** DownBeatTracking (strong baseline; CPU)
- **essentia** rhythm models (some TensorFlow-based; can use GPU depending on build)
- If you want “latest deep” later: introduce an embedding-based beat tracker, but keep scope contained.

Implementation
- Use the **mixture** or **drums** stem for beat tracking (configurable).
- Emit:
  - `beats[]` (every beat)
  - `downbeats[]` (bar starts)
  - `bpm_curve[]` segments (piecewise constant or piecewise linear)

Test
- For a known click track, verify beat count approximates expected.

---

### Phase 3 — Energy curves (per stem + overall)
**Deliverable**: `analysis/energy.json` with LLM-friendly curves.

What to compute
- RMS loudness curve (short-time energy)
- Optional: LUFS approximation if you bring in an R128 implementation (later)

LLM-friendly encoding
- Store curves at a modest resolution (e.g., 10 Hz) in JSON.
- Keep high-res arrays in a separate `.npz` only if needed later; JSON remains the primary contract.

Emit per track
- `mix`, `drums`, `bass`, `vocals`, `other`

Test
- Ensure energy curve timestamps are monotonic and within duration.

---

### Phase 4 — Drum event extraction (kick/snare/hat)
**Deliverable**: `analysis/onsets.json` with classified drum hits + confidence.

Recommended approach (ML-first)
- Use a pretrained **drum transcription** model on the **drums stem**.
  - Evaluate candidates (pick one; GPU preferred):
    - `omnizart` drum transcription (TF/Keras)
    - a PyTorch drum transcription model (preferred if available/maintained)
    - research option: MT3-style transcription (powerful but heavy)

Rules
- Do not degrade to heuristic spectral template matching if the model fails.

Output
- `events[]` each with `time`, `label` in `{kick,snare,hihat,other}` (allow `unknown`), `confidence`.

Test
- On a synthetic drum loop, confirm events exist and are within duration.

---

### Phase 5 — Vocal activity + phrase timing
**Deliverable**: `analysis/vocals.json` with voiced segments and phrase boundaries.

Model recommendation
- **Silero VAD** (PyTorch; simple; works on vocal stem)
- Later upgrade: `pyannote.audio` VAD/segmentation if you want more nuance (heavier)

Output
- `segments[]`: start/end + confidence
- `phrases[]`: merge short silences; include `energy_mean`, `energy_peak`

Test
- Ensure segments don’t overlap and are within song duration.

---

### Phase 6 — Sections (intro/verse/chorus/bridge…)
**Deliverable**: `analysis/sections.json` with boundaries + coarse labels.

ML-first pipeline (recommended)
1. Compute embeddings over time windows (e.g., 1–3s hop):
   - candidates: **OpenL3**, **musicnn**, or a modern CLAP-ish music embedding model (if stable on your GPU)
2. Build a self-similarity matrix + novelty curve (algorithmic step)
3. Peak-pick boundaries and form segments
4. Label segments with simple tags (intro/verse/chorus/bridge/outro) using repetition + energy heuristics

Failure rule
- If embedding model fails: omit sections entirely (write failure record), no handcrafted MFCC fallback.

Test
- Verify sections cover timeline end-to-end with no gaps/overlaps.

---

### Phase 7 — Pattern mining (kick/snare pattern library)
**Deliverable**: `show_plan/patterns.json` describing repeating patterns + occurrences.

Approach
- Quantize drum events onto the beat grid (e.g., 16th note bins).
- Build per-bar pattern vectors (binary or counts).
- Hash + cluster patterns (e.g., cosine similarity + threshold) to find repeats.
- Output:
  - canonical patterns (vectors + human label)
  - occurrences (start time, bars covered, confidence)

Test
- On a repeating loop, ensure at least one recurring pattern is found.

---

### Phase 8 — Show Plan IR (LLM-facing contract)
**Deliverable**: `show_plan/show_plan.json` + supporting IR files (`roles.json`, `moments.json`, `sections.json`).

Key idea
- The show plan should reference analysis artifacts via `includes` and provide a concise, LLM-readable summary.

Generate:
- `roles.json`: mapping of musical roles → tracks/features
- `moments.json`: “notable moments” (drops, risers, vocal entries, high energy peaks)
- `show_plan.json`: a compact index + meta

---

### Phase 9 — Plot analysis results
**Deliverable**: Generate visualization plots of the source waveform with inferred information overlaid, saved as PNG files in `analysis/plots/`.

Tasks
- Load source audio waveform from `temp_files/<song_slug>/audio/source.wav`.
- Load inferred data from `analysis/beats.json`, `analysis/energy.json`, `analysis/sections.json`, `analysis/vocals.json`.
- For each inferred type (beats, energy, sections, vocals), create a separate plot canvas:
  - Background: full source waveform (mono or stereo as appropriate).
  - Overlay: inferred data (e.g., vertical lines for beats, curves for energy).
  - Canvas size: 1920px wide x 200px height.
- Use matplotlib for plotting, ensuring headless compatibility.
- Save plots as `analysis/plots/beats.png`, `analysis/plots/energy.png`, etc.
- Handle missing data gracefully (e.g., if a step failed, skip that plot or plot empty).

Suggested deps
- `matplotlib>=3.5.0` (added to requirements.txt)

Test
- After running full analysis, verify 4 PNG files exist in `analysis/plots/` and are viewable.

---

## Output JSON contracts (LLM-friendly)

Design rules
- Always include `schema_version` and `generated_at` (ISO-8601).
- Always include `source` (models used + versions + device) when the artifact is produced by a model.
- Prefer explicit units: seconds, Hz, dB.
- Keep arrays ordered by time.
- Include failures in `analysis/run.json` at the step level (and optionally a top-level `failures[]` convenience list).

### Failure record contract (shared shape)

Any step can fail; the pipeline should continue. When it does, record:

```json
{
  "code": "MODEL_ERROR|IO_ERROR|VALIDATION_ERROR|DEPENDENCY_ERROR|UNKNOWN",
  "message": "human readable summary",
  "detail": "optional long detail (exception + context)",
  "exception_type": "ValueError",
  "retryable": false
}
```

### `analysis/run.json`
```json
{
  "schema_version": "1.0",
  "generated_at": "2026-02-03T12:34:56Z",
  "song": {
    "filename": "sono - keep control.mp3",
    "song_slug": "sono_keep_control",
    "sha256": "..."
  },
  "environment": {
    "python": "3.11.7",
    "platform": "linux",
    "cuda_available": true,
    "gpu": "NVIDIA ...",
    "packages": {
      "torch": "...",
      "demucs": "..."
    }
  },
  "steps": [
    {"name": "ingest", "status": "ok", "artifacts": ["analysis/timeline.json"], "seconds": 0.42},
    {"name": "stems", "status": "failed", "artifacts": [], "seconds": 12.3,
     "failure": {"code": "MODEL_ERROR", "message": "...", "detail": "..."}}
  ]
}
```

### `analysis/timeline.json`
```json
{
  "schema_version": "1.0",
  "song_slug": "sono_keep_control",
  "duration_s": 213.492,
  "sample_rate_hz": 44100,
  "channels": 2,
  "source_audio": {
    "original": "songs/sono - keep control.mp3",
    "decoded_wav": "temp_files/sono_keep_control/audio/source.wav"
  }
}
```

### `analysis/stems.json`
```json
{
  "schema_version": "1.0",
  "status": "ok",
  "model": {
    "name": "demucs",
    "variant": "htdemucs_ft",
    "device": "cuda",
    "half_precision": true
  },
  "stems": {
    "drums": "temp_files/sono_keep_control/stems/drums.wav",
    "bass": "temp_files/sono_keep_control/stems/bass.wav",
    "vocals": "temp_files/sono_keep_control/stems/vocals.wav",
    "other": "temp_files/sono_keep_control/stems/other.wav"
  }
}
```

### `analysis/beats.json`
```json
{
  "schema_version": "1.0",
  "source": {"name": "madmom", "model": "downbeat_rnn", "device": "cpu"},
  "beats": [0.49, 0.98, 1.47],
  "downbeats": [0.49, 2.45, 4.41],
  "tempo": {
    "unit": "bpm",
    "segments": [
      {"start_s": 0.0, "end_s": 30.0, "bpm": 122.0, "confidence": 0.84}
    ]
  }
}
```

### `analysis/energy.json`
```json
{
  "schema_version": "1.0",
  "fps": 10,
  "unit": "rms",
  "tracks": {
    "mix": {"times_s": [0.0, 0.1], "values": [0.02, 0.03]},
    "drums": {"times_s": [0.0, 0.1], "values": [0.01, 0.02]},
    "vocals": {"times_s": [0.0, 0.1], "values": [0.00, 0.00]}
  }
}
```

### `analysis/onsets.json`
```json
{
  "schema_version": "1.0",
  "source": {"name": "<drum_model>", "device": "cuda"},
  "events": [
    {"time_s": 12.345, "label": "kick", "confidence": 0.91},
    {"time_s": 12.567, "label": "snare", "confidence": 0.88}
  ]
}
```

### `analysis/vocals.json`
```json
{
  "schema_version": "1.0",
  "source": {"name": "silero_vad", "device": "cpu"},
  "segments": [
    {"start_s": 10.20, "end_s": 14.80, "confidence": 0.93}
  ],
  "phrases": [
    {"start_s": 10.20, "end_s": 14.80, "type": "vocal_phrase", "confidence": 0.90}
  ]
}
```

### `analysis/sections.json`
```json
{
  "schema_version": "1.0",
  "source": {"name": "openl3", "device": "cuda"},
  "sections": [
    {"start_s": 0.0, "end_s": 18.2, "label": "intro", "confidence": 0.62},
    {"start_s": 18.2, "end_s": 48.1, "label": "verse", "confidence": 0.55}
  ]
}
```

### `show_plan/patterns.json`
```json
{
  "schema_version": "1.0",
  "grid": {"subdivision": "1/16", "reference": "analysis/beats.json"},
  "patterns": [
    {
      "pattern_id": "p001",
      "type": "drums",
      "length_bars": 1,
      "tracks": {
        "kick": [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0]
      },
      "confidence": 0.77
    }
  ],
  "occurrences": [
    {"pattern_id": "p001", "start_s": 30.0, "bars": 8, "confidence": 0.72}
  ]
}
```

### `show_plan/roles.json`
```json
{
  "schema_version": "1.0",
  "roles": {
    "groove": {"primary": "drums", "features": ["beats", "kick", "snare"]},
    "bass": {"primary": "bass", "features": ["energy"]},
    "lead": {"primary": "vocals", "features": ["phrases", "energy"]}
  }
}
```

### `show_plan/moments.json`
```json
{
  "schema_version": "1.0",
  "moments": [
    {"time_s": 48.12, "type": "drop", "strength": 0.82, "evidence": ["energy_peak", "section_change"]},
    {"time_s": 62.00, "type": "vocal_entry", "strength": 0.74, "evidence": ["vad_start"]}
  ]
}
```

### `show_plan/show_plan.json` (index contract)
```json
{
  "includes": {
    "timeline": "../analysis/timeline.json",
    "stems": "../analysis/stems.json",
    "beats": "../analysis/beats.json",
    "energy": "../analysis/energy.json",
    "onsets": "../analysis/onsets.json",
    "vocals": "../analysis/vocals.json",
    "sections": "../analysis/sections.json",
    "roles": "./roles.json",
    "patterns": "./patterns.json",
    "moments": "./moments.json"
  },
  "meta": {
    "style": "hypnotic",
    "llm_version": "gpt-5.2",
    "confidence": 0.0,
    "notes": "Confidence is a placeholder until scoring is defined."
  }
}
```

---

## “Latest models” shortlist (practical first)

Prioritize these in this order:
1. **Demucs v4** for stems (GPU)
2. **Silero VAD** for vocal activity (CPU/GPU)
3. **OpenL3 / musicnn embeddings** for sections (GPU helps)
4. Beat tracking: pick **madmom** first for reliability; revisit with a newer deep model later
5. Drum transcription: evaluate **one** modern pretrained model and commit to it (no multi-backend complexity)

---

## Dependency + GPU notes

- Pin `torch` to a CUDA build compatible with your driver.
- Ensure `ffmpeg` is installed on the server.
- Keep `requirements.txt` minimal; split optional heavy deps into extras later (e.g., `requirements-drums.txt`).

---

## Definition of Done (per phase)

- CLI can run the phase in isolation.
- JSON validates against `pydantic` models.
- One deterministic test exists.
- Failures are recorded in `analysis/run.json`.
