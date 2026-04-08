# 🎵 Audio → Lighting Pipeline (Implementation Guide)

## 🧭 Overview

This document defines the full pipeline to transform audio into structured, LLM-ready data for DMX lighting generation.

Architecture is divided into **4 Layers (Epics)**:

- EPIC 1 → Audio Preprocessing
- EPIC 2 → Harmonic Summary
- EPIC 3 → Symbolic Event Summary
- EPIC 4 → Audio Energy Summary

---

# 🧱 EPIC 1 — Audio Preprocessing Pipeline

## 🎯 Goal
Prepare clean, structured inputs for feature extraction.

## 🧩 Story 1.1 — Stem Separation

### Tools
- Demucs

### Tasks
- Split audio into vocals, drums, bass, harmonic
- Normalize stems
- Cache results

### Output
```json
  "stems": {
    "bass": "path",
    "drums": "path",
    "harmonic": "path",
    "vocals": "path"
  }
}
```

---

## 🧩 Story 1.2 — Beat & Tempo Detection

### Tools
- Essentia

### Tasks
- Detect BPM
- Extract beats
- Compute bars

### Output
```json
{ 
  "tempo": 124, 
  "beats": [...], 
  "bars": [...] 
}
```

---

# 🎼 EPIC 2 — Harmonic Summary

## 🎯 Goal
Provide harmonic context

## 🧩 Story 2.1 — HPCP Feature Extraction

### Tools
- Essentia

### Tasks
- Extract HPCP from harmonic stem 
- Apply tuning correction 
- Aggregate per beat

### Acceptance
- Stable chroma representation across time

## 🧩 Story 2.2 — Chords

Phase 1: template matching + HMM 
Phase 2: CRNN model

### Tools
- Template + HMM
- Viterbi decoding

### Tasks 
- Generate chord probabilities 
- Decode with Viterbi 

### Output 
```json
  { "chords": [ {"time": 0.0, "label": "Am", "confidence": 0.82} ] } 
```
### Acceptance 
- Progression matches human expectation for test songs

## 🧩 Story 2.3 — Key & Tonal Center Detection
Detect global key

### Tools 
- Essentia key detection 

### Tasks 
- Detect global key 
- Optional: local key per section 

### Output 
```json
{ "key": "A minor" }
```

## 🧩 Story 2.4 — Harmonic Features

- tension
- cadence

### Tasks 
Extract: 
- root 
- chord quality 
- cadence detection 
- harmonic tension score 

### Output
```json
 { "harmonic_features": { "tension": 0.7, "cadence": "V-I" } }
```

---

# 🎹 EPIC 3 — Symbolic Event Summary

## 🎯 Goal
Translate audio into musical behavior

## 🧩 Story 3.1 — MIDI-like Transcription (CORE)

### Tools
- Basic Pitch (Spotify)

### Tasks
- Run transcription on:
  - harmonic stem (`other.wav` in current Demucs output)
  - bass stem (`bass.wav`)

- Extract:
  - note onsets
  - pitch (MIDI)
  - duration
  - velocity
  - confidence (optional)
- Merge note events into a unified timeline aligned to the canonical beat grid

### Output
```json
{
  "notes": [
    {"time": 1.23, "pitch": 64, "duration": 0.2, "velocity": 0.5, "confidence": 0.8}
  ]
}
```

### Acceptance
- Captures main harmonic structure from the harmonic stem
- Captures bass line movement clearly from the bass stem
- Timing aligns with the beat grid and analyzer section windows
- Feeds Story 3.2 feature engineering for density, contour, repetition, sustain, and bass motion

## 🧩 Story 3.2 — Feature Engineering

- density
- contour
- repetition
- bass motion

### Tasks
Compute:
- note density (per beat/bar) 
- active note count 
- pitch range 
- register centroid 
- melodic contour (slope) 
- bass movement 
- repetition score 
- sustain ratio 
- pitch bend activity

### Output
```json
Output { "symbolic_features": { "density": 0.65, "melodic_contour": "rising", "bass_motion": "stepwise" } }
```
## 🧩 Story 3.3 — Temporal Alignment

### Tasks
Snap notes to:
- beat grid (from EPIC 1.2)
- bars

## 🧩 Story 3.4 — LLM-Friendly Abstraction

### Tasks 
Convert raw features → descriptors 

### Output (IMPORTANT)
```json
{ "description": "Repeated staccato mid-register pattern with rising melodic contour and stable bass" } 
```

### Acceptance 
- Description is understandable by a musician
---

# 🔊 EPIC 4 — Audio Energy Summary

## 🎯 Goal
Capture physical intensity & motion

## 🧩 Story 4.1 — Features

### Tools
- Essentia

### Tasks
Extract:
- loudness
- spectral centroid
- spectral flux
- onset strength

### Output

(see energy_feature_schema.md)

## 🧩 Story 4.2 — Section Segmentation

- intro, verse, chorus

```json
[
  {
    "start": 0.0,
    "end": 35.82,
    "label": "Intro"
  },
  {
    "start": 35.82,
    "end": 50.14,
    "label": "Verse"
  }
]
```

## 🧩 Story 4.3 — Energy Features

- energy curve 
- intensity score 
- transient density

---

# 🔗 Final IR

{
  "tempo": {},
  "beats": [],
  "bars": [],
  "chords": [],
  "key": "",
  "notes": [],
  "symbolic_features": {},
  "description": "",
  "energy": {},
  "sections": []
}



----------
✅ EPIC 3 — Layer B: Symbolic Event Summary
🧩 Story 3.1 — MIDI-like Transcription ✅ (THIS is [Basic Pitch](https://github.com/spotify/basic-pitch))

Replace your current description with something more explicit:

🧩 Story 3.1 — MIDI-like Transcription (CORE)

Tools

- Basic Pitch (Spotify)

Tasks

- Run transcription on:
  - harmonic stem (polyphonic content)
  - bass stem (monophonic emphasis)

- Extract:
  - note onsets
  - pitch (MIDI)
  - duration
  - velocity (optional)

- Merge note events into unified timeline

Output

{
  "notes": [
    {"time": 1.23, "pitch": 64, "duration": 0.2}
  ]
}

Acceptance

- Captures main harmonic structure (chords/arpeggios)
- Captures bass line movement clearly
- Timing aligns with beat grid
🔁 How it connects to the rest of your system

This is where things get interesting (and powerful):

🔗 Feeds → Story 3.2 (Feature Engineering)

Basic Pitch output → becomes:

density
contour
repetition
sustain
bass motion

👉 Without Basic Pitch → Layer B collapses