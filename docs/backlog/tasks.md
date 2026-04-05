# 🧩 tasks.md — Atomic Implementation Plan (Copilot-Ready)

## 🎯 Purpose

This file breaks down the Audio → Lighting pipeline into **atomic, executable tasks** for VSCode Copilot or any LLM coding agent.

Each task should be:
- Small
- Testable
- Independent
- Incremental

---

# 🧱 EPIC 1 — Audio Preprocessing

## ✅ Task 1.1.1 — Create Stem Separation Module

- Create file: `audio/stem_separation.py`
- Implement function:
```python
def separate_stems(input_path: str, output_dir: str) -> dict:
    pass
```

- Use Demucs CLI
- Output paths for stems

---

## ✅ Task 1.1.2 — Normalize Audio

- Create file: `audio/normalize.py`
- Normalize all stems to consistent LUFS

---

## ✅ Task 1.1.3 — Cache Stems

- Save outputs under:
```
/cache/stems/{song_id}/
```

---

## ✅ Task 1.2.1 — Beat Detection

- Create file: `audio/beat_detection.py`
- Use Essentia
- Output:
```json
{
  "tempo": float,
  "beats": [],
  "bars": []
}
```

---

# 🎼 EPIC 2 — Harmonic

## ✅ Task 2.1.1 — HPCP Extraction

- File: `harmonic/hpcp.py`
- Input: harmonic stem
- Output: chroma vectors per frame

---

## ✅ Task 2.2.1 — Chord Templates

- File: `harmonic/chords.py`
- Implement major/minor templates

---

## ✅ Task 2.2.2 — Viterbi Decoder

- Decode chord sequence over time

---

## ✅ Task 2.3.1 — Key Detection

- File: `harmonic/key.py`
- Use Essentia

---

## ✅ Task 2.4.1 — Harmonic Features

- Compute:
  - tension
  - cadence

---

# 🎹 EPIC 3 — Symbolic

## ✅ Task 3.1.1 — Basic Pitch Wrapper

- File: `symbolic/basic_pitch_wrapper.py`

```python
def transcribe(audio_path: str) -> list:
    pass
```

- Output notes

---

## ✅ Task 3.1.2 — Merge Note Streams

- Combine harmonic + bass transcription

---

## ✅ Task 3.1.3 — Quantization

- Align notes to beat grid

---

## ✅ Task 3.2.1 — Density Calculation

- notes per beat/bar

---

## ✅ Task 3.2.2 — Contour Detection

- rising / falling / static

---

## ✅ Task 3.2.3 — Bass Motion

- stepwise / jumping

---

## ✅ Task 3.2.4 — Repetition Score

- detect repeating patterns

---

## ✅ Task 3.3.1 — Description Generator

- Convert features into text

Example:
```
"Repeated staccato mid-register pattern"
```

---

# 🔊 EPIC 4 — Energy

## ✅ Task 4.1.1 — Feature Extraction

- File: `energy/features.py`
- Extract:
  - loudness
  - spectral centroid
  - flux
  - onset

---

## ✅ Task 4.2.1 — Section Detection

- Segment into:
  - intro
  - verse
  - chorus

---

## ✅ Task 4.3.1 — Energy Metrics

- Compute:
  - intensity curve
  - transient density

---

# 🔗 FINAL TASK

## ✅ Task 5.1 — IR Builder

- File: `pipeline/build_ir.py`

```python
def build_ir(song_id: str) -> dict:
    pass
```

- Merge all outputs into single JSON

---

# 🚀 Execution Order

1. EPIC 1
2. EPIC 2
3. EPIC 3
4. EPIC 4
5. IR Builder

---

# 🧠 Copilot Instructions

- Implement ONE task at a time
- Write tests for each module
- Avoid coupling between layers
- Use clear JSON contracts

---

# 🎯 Definition of Done

- All modules implemented
- IR file generated per song
- Outputs are LLM-ready
