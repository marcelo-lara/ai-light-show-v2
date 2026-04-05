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
{
  "stems": {
    "bass": "path",
    "drums": "path",
    "harmonic": "path",
    "vocals": "path"
  }
}

---

## 🧩 Story 1.2 — Beat & Tempo Detection

### Tools
- Essentia

### Tasks
- Detect BPM
- Extract beats
- Compute bars

---

# 🎼 EPIC 2 — Harmonic Summary

## 🎯 Goal
Provide harmonic context

## 🧩 Story 2.1 — HPCP

- Extract chroma
- Aggregate per beat

## 🧩 Story 2.2 — Chords

- Template + HMM
- Viterbi decoding

## 🧩 Story 2.3 — Key

- Detect global key

## 🧩 Story 2.4 — Harmonic Features

- tension
- cadence

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
  - velocity or confidence
- Merge note events into a unified timeline aligned to the canonical beat grid

### Output
{
  "notes": [
    {"time": 1.23, "pitch": 64, "duration": 0.2}
  ]
}

### Acceptance
- Captures main harmonic structure from the harmonic stem
- Captures bass line movement clearly from the bass stem
- Timing aligns with the beat grid and analyzer section windows
- Feeds Story 3.2 feature engineering for density, contour, repetition, sustain, and bass motion

## 🧩 Story 3.2 — Features

- density
- contour
- repetition
- bass motion

## 🧩 Story 3.3 — Description

- Convert to human-readable text

---

# 🔊 EPIC 4 — Audio Energy Summary

## 🎯 Goal
Capture intensity

## 🧩 Story 4.1 — Features

- loudness
- centroid
- flux
- onset

## 🧩 Story 4.2 — Sections

- intro, verse, chorus

## 🧩 Story 4.3 — Energy Metrics

- intensity
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