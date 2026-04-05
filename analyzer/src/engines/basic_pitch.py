from __future__ import annotations

from pathlib import Path
from typing import Any


def transcribe_notes(audio_path: str | Path) -> list[dict[str, Any]]:
    try:
        from basic_pitch.inference import predict
    except Exception:
        return []
    try:
        model_output, midi_data, note_events = predict(str(Path(audio_path).expanduser().resolve()))
        del model_output, midi_data
    except Exception:
        return []
    normalized: list[dict[str, Any]] = []
    for event in note_events:
        start_s = float(getattr(event, "start_time_s", 0.0) or 0.0)
        end_s = float(getattr(event, "end_time_s", start_s) or start_s)
        pitch_midi = int(getattr(event, "pitch", 0) or 0)
        normalized.append(
            {
                "start_s": start_s,
                "end_s": end_s,
                "pitch_midi": pitch_midi,
                "pitch_name": _pitch_name(pitch_midi),
                "confidence": float(getattr(event, "confidence", 0.0) or 0.0),
                "source_part": "mix",
            }
        )
    return normalized


def transcribe_sources(sources: dict[str, str | Path]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for source_part, audio_path in sources.items():
        for note in transcribe_notes(audio_path):
            merged.append({**note, "source_part": source_part})
    return sorted(merged, key=lambda item: (float(item.get("start_s", 0.0) or 0.0), int(item.get("pitch_midi", 0) or 0)))


def _pitch_name(pitch_midi: int) -> str:
    if pitch_midi <= 0:
        return ""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (pitch_midi // 12) - 1
    return f"{names[pitch_midi % 12]}{octave}"