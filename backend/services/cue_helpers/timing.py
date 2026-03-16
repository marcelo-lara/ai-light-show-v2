from __future__ import annotations


def beatToTimeMs(beat_count: float, bpm: float) -> float:
    bpm_f = float(bpm)
    if bpm_f <= 0.0:
        raise ValueError("bpm_must_be_positive")
    return float(beat_count) * (60000.0 / bpm_f)


def beats_to_seconds(beat_count: float, bpm: float) -> float:
    return beatToTimeMs(beat_count, bpm) / 1000.0
