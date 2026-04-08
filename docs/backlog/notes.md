# Audio To Lighting Notes

## Purpose

This file replaces the rough GPT notes with a repo-accurate reference.

It does three jobs:

1. Records whether the GPT notes match the current repository direction.
2. Lists the next concrete implementation tasks for harmonic, symbolic, energy, IR, and score generation depth.
3. Compares the GPT-style flat IR contract with the current repo-native `music_feature_layers.json` shape.

The current analysis pipeline writes canonical metadata under `data/output/{song}/` and companion artifacts under `data/artifacts/{song}/`.

---

## Same Page Summary

Short answer: yes on direction, not yet on implementation depth.

The current repository now matches these high-level goals:

- Audio is processed through the analyzer task pipeline, not through a separate standalone pipeline.
- The analyzer produces three additive layer artifacts:
  - `layer_a_harmonic.json`
  - `layer_b_symbolic.json`
  - `layer_c_energy.json`
- Those layers are merged into `music_feature_layers.json`.
- The final markdown artifact is `lighting_score.md`.
- Symbolic transcription now uses Basic Pitch on the harmonic stem and bass stem, then merges and beat-aligns those note events.

The current repository does not yet match these GPT notes in full:

- Harmonic analysis is not yet a full HPCP plus chord-probability plus Viterbi inference stack.
- Symbolic feature engineering is still shallow compared with the target list.
- Energy analysis is still mostly a consolidation layer over existing analyzer outputs rather than a deeper dedicated feature-engineering pass.
- The current IR shape is nested and repo-native, not the flatter GPT sketch.

So the destination is aligned, but the implementation is still in an early integration phase.

---

## Current Repo-Native Pipeline

### Canonical flow

The analyzer-native full-artifact flow is currently:

1. `init-song`
2. `split-stems`
3. `beat-finder` or `import-moises`
4. `find_chords`
5. `find_sections`
6. `essentia-analysis`
7. `find-song-features`
8. `stereo-analysis`
9. `find-chord-patterns`
10. `find-stem-patterns`
11. `harmonic-layer`
12. `symbolic-layer`
13. `energy-layer`
14. `build-music-feature-layers`
15. `generate-md`

### Current implementation anchors

- Playlist orchestration: `analyzer/src/playlists/full_artifact.py`
- Task catalog: `analyzer/src/tasks/catalog.py`
- Harmonic layer builder: `analyzer/src/feature_layers/harmonic.py`
- Symbolic layer builder: `analyzer/src/feature_layers/symbolic.py`
- Energy layer builder: `analyzer/src/feature_layers/energy.py`
- IR builder: `analyzer/src/feature_layers/ir.py`
- Basic Pitch wrapper: `analyzer/src/engines/basic_pitch.py`
- Lighting score renderer: `analyzer/src/report_tool/generate_md.py`

### Current artifact set

Current canonical and additive artifacts under `data/output/{song}/` and `data/artifacts/{song}/`:

- `info.json`
- canonical beats file
- `sections.json`
- `hints.json`
- `features.json`
- `chord_patterns.json`
- `stem_patterns.json`
- `layer_a_harmonic.json`
- `layer_b_symbolic.json`
- `layer_c_energy.json`
- `music_feature_layers.json`
- `lighting_score.md`

---

## Status By Epic

### EPIC 1 - Audio Preprocessing

Status: mostly aligned.

Implemented now:

- Demucs stem splitting is already part of the analyzer.
- Beat and tempo data already feed canonical analyzer timing artifacts.
- Stems are persisted and reused by downstream tasks.

Still to deepen:

- explicit stem normalization policy if needed
- clearer stem role metadata for downstream symbolic and harmonic processing

### EPIC 2 - Harmonic Summary

Status: partially aligned.

Implemented now:

- harmonic layer artifact exists
- global key is pulled from current analyzer metadata
- chord events are derived from canonical beat rows
- chord patterns are attached when present
- section-level harmony summaries are generated

Not implemented yet:

- dedicated HPCP-to-chord inference path in the layer builder
- chord probability tracking
- Viterbi decoding
- real cadence detection
- meaningful harmonic tension scoring beyond simple density-based summaries

### EPIC 3 - Symbolic Event Summary

Status: partially aligned, materially closer than before.

Implemented now:

- Basic Pitch is integrated
- transcription runs on the harmonic stem and bass stem when available
- note events are merged into one timeline
- notes are aligned to nearest canonical beats
- section-level symbolic summaries exist
- density-per-bar and simple contour summaries exist

Not implemented yet:

- richer bass motion classification
- repetition and motif detection
- sustain ratio
- pitch range and register centroid
- stronger phrase-level abstraction
- richer LLM-facing symbolic descriptions

### EPIC 4 - Energy Summary

Status: partially aligned.

Implemented now:

- global energy summary exists
- section energy summary exists
- accent candidates are derived from hints
- notable peaks and dips are summarized

Not implemented yet:

- deeper spectral centroid and flux interpretation
- stronger transient-density engineering
- more explicit low-level feature aggregation for prompt use

---

## Concrete Next Tasks

This is the repo-native implementation handoff derived from the GPT notes.

### Next Harmonic Tasks

1. Enrich `analyzer/src/feature_layers/harmonic.py` with real HPCP-backed summaries using current Essentia artifacts before inventing a second harmonic engine.
2. Add cadence detection from chord-event transitions and section endings.
3. Add a more meaningful harmonic tension score based on change density, unstable harmony windows, and cadence resolution.
4. Extend `layer_a_harmonic.json` tests to verify cadence notes and tension peaks.

### Next Symbolic Tasks

1. Extend `analyzer/src/feature_layers/symbolic.py` to compute:
   - repetition score
   - bass movement classification
   - sustain ratio
   - pitch range
   - register centroid
2. Add phrase-level grouping using canonical beat windows.
3. Improve symbolic descriptions so they read more like musician-facing texture summaries.
4. Extend `layer_b_symbolic.json` tests to verify harmonic-stem and bass-stem contribution separately.

### Next Energy Tasks

1. Extend `analyzer/src/feature_layers/energy.py` to summarize centroid, flux, and onset behavior from current Essentia artifacts instead of placeholder text.
2. Add section-level energy-curve descriptors that better explain ramps, plateaus, and releases.
3. Improve accent candidate ranking so score generation can choose better event anchors.

### Next IR Tasks

1. Extend `analyzer/src/feature_layers/ir.py` so `section_cards` include more explicit harmonic, symbolic, and energy phrasing.
2. Add a clearer prompt-oriented `description` surface for downstream lighting logic.
3. Keep the nested repo-native structure; do not flatten the IR just to mirror GPT notes.

### Next Lighting Score Tasks

1. Extend `analyzer/src/report_tool/generate_md.py` so more of `analyzer/docs/lighting_score_template.md` is populated from `music_feature_layers.json`.
2. Add dedicated sections for harmonic summary and symbolic summary in the rendered score.
3. Use the richer `section_cards` to improve per-section narrative and execution guidance.

---

## IR Contract Comparison

The GPT notes propose a flatter contract:

```json
{
  "tempo": {},
  "beats": [],
  "bars": [],
  "chords": [],
  "key": "",
  "harmonic_features": {},
  "notes": [],
  "symbolic_features": {},
  "description": "",
  "energy": {},
  "sections": []
}
```

The current repo-native IR is intentionally more structured.

### Field-by-field mapping

| GPT field | Current IR location | Status | Notes |
|---|---|---|---|
| `tempo` | `metadata.bpm` | aligned but renamed | repo stores BPM under metadata instead of a standalone tempo object |
| `beats` | `timeline.beats` | aligned | sourced from canonical analyzer beats |
| `bars` | `timeline.bars` | aligned | derived from canonical beats |
| `chords` | `layers.harmonic.chord_events` | aligned but nested | harmonic events are part of the harmonic layer |
| `key` | `metadata.key` and `layers.harmonic.global_key` | aligned but duplicated by design | metadata carries convenient top-level key, harmonic layer keeps provenance |
| `harmonic_features` | `layers.harmonic` | aligned but broader | current harmonic layer includes summary, chord patterns, section harmony, and validation notes |
| `notes` | `layers.symbolic.note_events` | aligned but nested | symbolic note events remain inside the symbolic layer |
| `symbolic_features` | `layers.symbolic.symbolic_summary`, `density_per_bar`, `section_symbolic`, others | aligned but broader | current symbolic layer separates summary from detailed derived lists |
| `description` | `layers.symbolic.symbolic_summary.description` and `structure_summary` | partially aligned | repo currently splits descriptive text by responsibility |
| `energy` | `layers.energy` | aligned but broader | current energy layer includes global, sectional, and accent-oriented summaries |
| `sections` | `timeline.sections` | aligned | canonical analyzer sections remain the timeline source of truth |

### Additional repo-native fields

The current IR also contains fields not present in the GPT sketch:

- `schema_version`
- `song_id`
- `source_song_path`
- `generated_from`
- `metadata`
- `timeline.accent_windows`
- `layers`
- `structure_summary`
- `section_cards`
- `mapping_rules`
- `generation_notes`

These are intentional and useful. They help with provenance, deterministic rendering, and LLM-oriented score generation.

### Decision

Do not flatten the current IR to match the GPT sketch.

Keep the current nested structure and continue filling it out. It is better suited to the repository's analyzer-owned contract and lighting-score generation flow.

---

## Exact Areas Where We Are Not Yet On The Same Page

These are the remaining mismatches between the GPT notes and the repo:

1. Harmonic depth is still too shallow compared with the target note.
2. Symbolic transcription source selection is aligned, but symbolic feature engineering is still incomplete.
3. Energy engineering still relies on summary placeholders for some spectral interpretations.
4. The lighting score generator does not yet surface all three layers as fully as the target design implies.
5. The GPT notes still describe a conceptual pipeline, while the repo uses analyzer-native tasks and additive artifacts over the existing metadata contract.

---

## Repo Decisions

These decisions should remain stable unless there is a deliberate redesign:

1. The analyzer task system remains the only pipeline.
2. The canonical metadata roots remain `data/output/{song}/` and `data/artifacts/{song}/`.
3. `music_feature_layers.json` remains the single LLM-ready IR for score generation.
4. `lighting_score.md` remains the canonical markdown output.
5. The IR stays nested and analyzer-owned rather than mirroring a flatter external sketch.

---

## Working Conclusion

We are on the same page about what the system should become.

We are not yet on the same page if the GPT notes are read as a description of current implementation.

Treat them as target-state guidance.
Treat the current analyzer code as the actual source of truth.
Use the next-task list above to close the remaining gaps.
