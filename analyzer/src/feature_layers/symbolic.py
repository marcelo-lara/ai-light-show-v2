from __future__ import annotations

from pathlib import Path
from typing import Any

from .symbolic_support import bass_motion_summary, density_trend, median_beat_duration, melodic_contour, phrase_contours, phrase_description, pitch_range, register_centroid, repeated_motifs, sustain_ratio
from ..storage.song_meta import canonical_beats_path, load_json_file, load_sections


def build_symbolic_layer(song_path: Path, meta_path: Path, notes: list[dict[str, Any]] | None = None, stems_used: list[str] | None = None) -> dict[str, Any]:
    meta_dir = meta_path / song_path.stem
    sections = load_sections(meta_dir)
    beats_file = canonical_beats_path(song_path, meta_path)
    beats_rows = load_json_file(beats_file) if beats_file.exists() else []
    beats = [row for row in beats_rows if isinstance(row, dict)]
    note_events = _normalize_notes(notes or [], sections, beats)
    density_per_bar = _density_per_bar(note_events)
    beat_duration = median_beat_duration(beats)
    repetition_score, repetition_level, motifs = repeated_motifs(note_events, beat_duration)
    bass_motion, bass_movement_events = bass_motion_summary(note_events)
    phrases = phrase_contours(sections, beats, note_events, beat_duration)
    section_symbolic = [_section_symbolic(section, note_events, phrases, beat_duration, bass_motion, repetition_level, repetition_score) for section in sections]
    note_range = pitch_range(note_events)
    register = register_centroid(note_events)
    return {
        "schema_version": "1.0",
        "song_id": song_path.stem,
        "generated_from": {
            "source_song_path": str(song_path),
            "sections_file": str(meta_dir / "sections.json"),
            "beats_file": str(beats_file),
        },
        "transcription_source": {
            "engine": "basic-pitch",
            "model_version": "unknown",
            "stems_used": stems_used or ["mix"],
        },
        "note_events": note_events[:256],
        "symbolic_summary": {
            "texture": "sparse" if len(note_events) < 32 else "layered",
            "melodic_contour": melodic_contour(note_events),
            "bass_motion": bass_motion,
            "repetition_level": repetition_level,
            "repetition_score": repetition_score,
            "density_trend": density_trend(density_per_bar),
            "sustain_ratio": sustain_ratio(note_events, beat_duration),
            "pitch_range": note_range,
            "register_centroid": register,
            "description": phrase_description(note_events, beat_duration) if note_events else "No symbolic summary available.",
        },
        "density_per_bar": density_per_bar,
        "phrase_contours": phrases,
        "bass_movement_events": bass_movement_events,
        "repeated_motifs": motifs,
        "section_symbolic": section_symbolic,
        "validation_notes": [] if note_events else ["Basic Pitch notes unavailable; symbolic layer contains empty note inventory."],
    }


def _normalize_notes(notes: list[dict[str, Any]], sections: list[dict[str, Any]], beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, note in enumerate(notes):
        start_s = round(float(note.get("start_s", 0.0) or 0.0), 3)
        end_s = round(float(note.get("end_s", start_s) or start_s), 3)
        section_name = _section_name(start_s, sections)
        beat_row = _nearest_beat(beats, start_s)
        normalized.append(
            {
                "start_s": start_s,
                "end_s": max(end_s, start_s),
                "duration_s": round(max(end_s - start_s, 0.0), 3),
                "pitch_midi": int(note.get("pitch_midi", 0) or 0),
                "pitch_name": str(note.get("pitch_name") or ""),
                "velocity": float(note.get("velocity", note.get("confidence", 0.0)) or 0.0),
                "confidence": float(note.get("confidence", 0.0) or 0.0),
                "source_part": str(note.get("source_part") or "mix"),
                "bar_index": int((beat_row or {}).get("bar", note.get("bar_index", index // 4)) or 0),
                "beat_index": int((beat_row or {}).get("beat", note.get("beat_index", index)) or 0),
                "section_name": section_name,
            }
        )
    return sorted(normalized, key=lambda item: (item["start_s"], item["pitch_midi"]))


def _nearest_beat(beats: list[dict[str, Any]], time_value: float) -> dict[str, Any] | None:
    if not beats:
        return None
    return min(beats, key=lambda beat: abs(float(beat.get("time", 0.0) or 0.0) - time_value))


def _density_per_bar(note_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[int, int] = {}
    for note in note_events:
        counts[note["bar_index"]] = counts.get(note["bar_index"], 0) + 1
    return [
        {"bar_index": bar_index, "note_count": count, "density_label": "high" if count >= 8 else "mid" if count >= 4 else "low", "section_name": ""}
        for bar_index, count in sorted(counts.items())
    ]


def _section_symbolic(section: dict[str, Any], note_events: list[dict[str, Any]], phrases: list[dict[str, Any]], beat_duration: float, bass_motion: str, repetition_level: str, repetition_score: float) -> dict[str, Any]:
    notes = [note for note in note_events if note.get("section_name") == section["name"]]
    section_phrases = [phrase for phrase in phrases if phrase.get("section_name") == section["name"]]
    note_range = pitch_range(notes)
    register = register_centroid(notes)
    return {
        "section_id": f"{section['name'].lower().replace(' ', '-')}-{section['start_s']:.2f}",
        "section_name": section["name"],
        "note_density": len(notes),
        "contour": melodic_contour(notes),
        "bass_motion": bass_motion,
        "repetition": repetition_level,
        "repetition_score": repetition_score,
        "texture": "sparse" if len(notes) < 12 else "layered",
        "sustain_ratio": sustain_ratio(notes, beat_duration),
        "pitch_range": note_range,
        "register_centroid": register,
        "phrase_count": len(section_phrases),
        "summary": phrase_description(notes, beat_duration) if notes else "No symbolic summary available.",
    }


def _section_name(time_value: float, sections: list[dict[str, Any]]) -> str:
    for index, section in enumerate(sections):
        is_last = index == len(sections) - 1
        if section["start_s"] <= time_value < section["end_s"] or (is_last and section["start_s"] <= time_value <= section["end_s"]):
            return section["name"]
    return ""