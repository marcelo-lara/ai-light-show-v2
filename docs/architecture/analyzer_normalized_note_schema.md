# 🎼 NORMALIZED NOTE SCHEMA — IR SPECIFICATION

## 🎯 Goal

Define a **standard, normalized representation of musical notes** extracted from audio (e.g., via Basic Pitch), to be used across the pipeline.

This schema is:

- LLM-friendly
- Time-aligned with beats/bars
- Deterministic for downstream processing (DMX, analytics)

---

# 🧱 Core Principles

1. **Time is absolute (seconds) + musical (beats/bars)**
2. **Pitch is MIDI-based**
3. **All notes are atomic events**
4. **Optional fields are explicitly nullable**
5. **Quantization is preserved separately (non-destructive)**

---

# 📦 Note Object Schema

```json
{
  "id": "note_000001",
  "time": 1.230,
  "duration": 0.200,
  "end": 1.430,

  "pitch": 64,
  "note_name": "E4",
  "octave": 4,

  "velocity": 0.78,

  "confidence": 0.91,

  "source": "harmonic",

  "beat": 3.5,
  "bar": 2,
  "position_in_bar": 0.75,

  "quantized": {
    "time": 1.250,
    "duration": 0.250,
    "beat": 3.5,
    "grid": "1/16"
  },

  "flags": {
    "is_bass": false,
    "is_chord_tone": true,
    "is_repeated": false
  }
}
```

---

# 🧩 Field Definitions

## ⏱ Time Domain

| Field | Type | Description |
|------|------|------------|
| time | float | Note onset (seconds) |
| duration | float | Duration (seconds) |
| end | float | time + duration |

---

## 🎵 Pitch Domain

| Field | Type | Description |
|------|------|------------|
| pitch | int | MIDI note number |
| note_name | string | Human-readable (e.g., C4, F#3) |
| octave | int | Extracted from MIDI |

---

## 🔊 Dynamics

| Field | Type | Description |
|------|------|------------|
| velocity | float | Normalized (0–1) |
| confidence | float | Model confidence |

---

## 🧠 Source Tracking

| Field | Type | Description |
|------|------|------------|
| source | string | "bass", "harmonic", "vocals" |

---

## 🧭 Musical Alignment

| Field | Type | Description |
|------|------|------------|
| beat | float | Beat position |
| bar | int | Bar index |
| position_in_bar | float | 0–1 |

---

## 🎯 Quantization Block

Non-destructive alignment to grid.

| Field | Type | Description |
|------|------|------------|
| quantized.time | float | Snapped onset |
| quantized.duration | float | Snapped duration |
| quantized.beat | float | Snapped beat |
| quantized.grid | string | e.g. "1/16" |

---

## 🚩 Flags

| Field | Type | Description |
|------|------|------------|
| is_bass | bool | True if from bass stem |
| is_chord_tone | bool | Matches detected chord |
| is_repeated | bool | Pattern repetition |

---

# 📚 Collection Schema

All notes are grouped:

```json
{
  "notes": [ ... ],
  "metadata": {
    "total_notes": 1243,
    "time_range": [0, 180],
    "sources": ["bass", "harmonic"]
  }
}
```

---

# ⚙️ Implementation Guidelines

## ID Generation

```
note_{incremental_id}
```

---

## Pitch Conversion

```
note_name = MIDI → (C, C#, D...) + octave
```

---

## Beat Alignment

Use EPIC 1 beat grid:

```
beat_index = find_nearest_beat(time)
```

---

## Quantization Strategy

- Keep BOTH:
  - raw timing
  - quantized timing
- Never overwrite original values

---

# 🚀 Future Extensions

- chord_id reference
- voice separation (polyphony grouping)
- articulation (staccato, legato)
- MIDI export compatibility

---

# 🎯 Key Insight

This schema is the **bridge between audio and intelligence**:

- Upstream → raw transcription
- Downstream → lighting, LLM reasoning, behavior

👉 If this schema is clean, everything else becomes easier.
