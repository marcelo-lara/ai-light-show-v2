🧱 EPIC 1 — Audio Preprocessing Pipeline
🎯 Goal

Prepare clean, structured inputs for feature extraction.

🧩 Story 1.1 — Stem Separation

Tools

Demucs (preferred)

Tasks

 Split audio into:
vocals
drums
bass
harmonic (other)

 Normalize stems
 Cache results

Output

{
  "stems": {
    "bass": "...",
    "drums": "...",
    "harmonic": "...",
    "vocals": "..."
  }
}

Acceptance

Harmonic stem is clean enough for chord detection
Bass stem is usable for root tracking
🧩 Story 1.2 — Beat & Tempo Detection

Tools

Essentia

Tasks

 Detect BPM
 Extract beat timestamps
 Compute bars (time signature assumption = 4/4 initially)

Output

{
  "tempo": 124,
  "beats": [...],
  "bars": [...]
}

Acceptance

Beat grid aligns with audible rhythm
🎼 EPIC 2 — Layer A: Harmonic Summary
🎯 Goal

Provide LLM-readable harmonic context

🧩 Story 2.1 — HPCP Feature Extraction

Tools

Essentia

Tasks

 Extract HPCP from harmonic stem
 Apply tuning correction
 Aggregate per beat

Acceptance

Stable chroma representation across time
🧩 Story 2.2 — Chord Detection

Options

Phase 1: template matching + HMM
Phase 2: CRNN model

Tasks

 Generate chord probabilities
 Decode with Viterbi

Output

{
  "chords": [
    {"time": 0.0, "label": "Am", "confidence": 0.82}
  ]
}

Acceptance

Progression matches human expectation for test songs
🧩 Story 2.3 — Key & Tonal Center Detection

Tools

Essentia key detection

Tasks

 Detect global key
 Optional: local key per section

Output

{
  "key": "A minor"
}
🧩 Story 2.4 — Harmonic Features

Tasks

 Extract:
root
chord quality
cadence detection
harmonic tension score

Output

{
  "harmonic_features": {
    "tension": 0.7,
    "cadence": "V-I"
  }
}
🎹 EPIC 3 — Layer B: Symbolic Event Summary
🎯 Goal

Translate audio into musical behavior

🧩 Story 3.1 — MIDI-like Transcription

Tools

basic-pitch

Tasks

 Run per stem (harmonic + bass)
 Merge note events

Output

{
  "notes": [
    {"time": 1.23, "pitch": 64, "duration": 0.2}
  ]
}

Acceptance

Captures main harmonic + melodic motion
🧩 Story 3.2 — Feature Engineering (CRITICAL)

Tasks

 Compute:
note density (per beat/bar)
active note count
pitch range
register centroid
melodic contour (slope)
bass movement
repetition score
sustain ratio
pitch bend activity

Output

{
  "symbolic_features": {
    "density": 0.65,
    "melodic_contour": "rising",
    "bass_motion": "stepwise"
  }
}
🧩 Story 3.3 — LLM-Friendly Abstraction

Tasks

 Convert raw features → descriptors

Output (IMPORTANT)

{
  "description": "Repeated staccato mid-register pattern with rising melodic contour and stable bass"
}

Acceptance

Description is understandable by a musician
🔊 EPIC 4 — Layer C: Audio Energy Summary
🎯 Goal

Capture physical intensity & motion

🧩 Story 4.1 — Low-Level Features

Tools

Essentia

Tasks

 Extract:
loudness
spectral centroid
spectral flux
onset strength
🧩 Story 4.2 — Section Segmentation

Tasks

 Detect sections:
intro
verse
chorus
bridge

Output

{
  "sections": [
    {"start": 0, "type": "intro"},
    {"start": 30, "type": "verse"}
  ]
}
🧩 Story 4.3 — Energy Features

Tasks

 Compute:
energy curve
intensity score
transient density