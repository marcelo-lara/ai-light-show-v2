from __future__ import annotations

from statistics import median
from typing import Any


def bass_motion_summary(note_events: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    bass_notes = [note for note in note_events if note.get("source_part") == "bass"] or _lowest_voice(note_events)
    if len(bass_notes) < 2:
        return "unknown", []
    events: list[dict[str, Any]] = []
    for previous, current in zip(bass_notes, bass_notes[1:]):
        interval = int(current["pitch_midi"] - previous["pitch_midi"])
        movement = "repeat" if interval == 0 else "step" if abs(interval) <= 2 else "leap"
        events.append(
            {
                "time": current["start_s"],
                "from_pitch": previous["pitch_name"],
                "to_pitch": current["pitch_name"],
                "interval_semitones": interval,
                "direction": "up" if interval > 0 else "down" if interval < 0 else "hold",
                "movement_type": movement,
            }
        )
    step_share = sum(1 for item in events if item["movement_type"] == "step") / len(events)
    leap_share = sum(1 for item in events if item["movement_type"] == "leap") / len(events)
    hold_share = sum(1 for item in events if item["movement_type"] == "repeat") / len(events)
    if hold_share >= 0.6:
        return "pedal", events
    if step_share >= 0.6:
        return "stepwise", events
    if leap_share >= 0.4:
        return "leaping", events
    return "mixed", events


def density_trend(density_per_bar: list[dict[str, Any]]) -> str:
    counts = [int(item.get("note_count", 0) or 0) for item in density_per_bar]
    if len(counts) < 2:
        return "unknown"
    deltas = [current - previous for previous, current in zip(counts, counts[1:])]
    if all(abs(delta) <= 1 for delta in deltas):
        return "steady"
    if sum(1 for delta in deltas if delta > 0) >= len(deltas) * 0.7:
        return "rising"
    if sum(1 for delta in deltas if delta < 0) >= len(deltas) * 0.7:
        return "falling"
    return "wave"


def phrase_contours(sections: list[dict[str, Any]], beats: list[dict[str, Any]], note_events: list[dict[str, Any]], beat_duration: float) -> list[dict[str, Any]]:
    phrases: list[dict[str, Any]] = []
    for section in sections:
        for index, window in enumerate(_phrase_windows(section, beats), start=1):
            notes = [note for note in note_events if window["start_s"] <= note["start_s"] <= window["end_s"]]
            if not notes:
                continue
            note_range = pitch_range(notes)
            phrases.append(
                {
                    "section_name": section["name"],
                    "phrase_index": index,
                    "start_s": window["start_s"],
                    "end_s": window["end_s"],
                    "note_count": len(notes),
                    "contour": melodic_contour(notes),
                    "sustain_ratio": sustain_ratio(notes, beat_duration),
                    "pitch_range": note_range,
                    "register_centroid": register_centroid(notes),
                    "summary": phrase_description(notes, beat_duration),
                }
            )
    return phrases


def phrase_description(note_events: list[dict[str, Any]], beat_duration: float) -> str:
    note_range = pitch_range(note_events)
    centroid = register_centroid(note_events)
    return f"{len(note_events)} notes, {melodic_contour(note_events)} contour, {centroid['label']} register, {note_range['semitones']} semitone span, sustain {sustain_ratio(note_events, beat_duration):.2f}."


def pitch_range(note_events: list[dict[str, Any]]) -> dict[str, Any]:
    pitches = sorted(note["pitch_midi"] for note in note_events if int(note.get("pitch_midi", 0) or 0) > 0)
    if not pitches:
        return {"min_midi": 0, "max_midi": 0, "min_pitch": "", "max_pitch": "", "semitones": 0}
    lowest = note_by_pitch(note_events, pitches[0])
    highest = note_by_pitch(note_events, pitches[-1])
    return {
        "min_midi": pitches[0],
        "max_midi": pitches[-1],
        "min_pitch": str((lowest or {}).get("pitch_name") or ""),
        "max_pitch": str((highest or {}).get("pitch_name") or ""),
        "semitones": pitches[-1] - pitches[0],
    }


def register_centroid(note_events: list[dict[str, Any]]) -> dict[str, Any]:
    pitches = [note["pitch_midi"] for note in note_events if int(note.get("pitch_midi", 0) or 0) > 0]
    if not pitches:
        return {"midi": 0.0, "label": "unknown"}
    centroid = sum(pitches) / len(pitches)
    label = "low" if centroid < 48 else "mid" if centroid < 72 else "high"
    return {"midi": round(centroid, 2), "label": label}


def repeated_motifs(note_events: list[dict[str, Any]], beat_duration: float) -> tuple[float, str, list[dict[str, Any]]]:
    melodic = [note for note in note_events if note.get("source_part") != "bass"] or note_events
    if len(melodic) < 3:
        return 0.0, "low", []
    motif_map: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for index in range(len(melodic) - 2):
        window = melodic[index:index + 3]
        signature = (
            window[1]["pitch_midi"] - window[0]["pitch_midi"],
            window[2]["pitch_midi"] - window[1]["pitch_midi"],
            _duration_bucket(window[0]["duration_s"], beat_duration),
            _duration_bucket(window[1]["duration_s"], beat_duration),
            _duration_bucket(window[2]["duration_s"], beat_duration),
        )
        motif_map.setdefault(signature, []).append(window[0])
    repeated = [{"motif": list(signature), "occurrences": len(rows), "first_seen_s": rows[0]["start_s"]} for signature, rows in motif_map.items() if len(rows) >= 2]
    motif_total = max(len(melodic) - 2, 1)
    score = round(sum(item["occurrences"] for item in repeated) / motif_total, 3)
    level = "high" if score >= 0.45 else "medium" if score >= 0.2 else "low"
    return score, level, sorted(repeated, key=lambda item: (-item["occurrences"], item["first_seen_s"]))[:8]


def sustain_ratio(note_events: list[dict[str, Any]], beat_duration: float) -> float:
    if not note_events:
        return 0.0
    threshold = max(beat_duration * 0.75, 0.25)
    sustained = sum(1 for note in note_events if float(note.get("duration_s", 0.0) or 0.0) >= threshold)
    return round(sustained / len(note_events), 3)


def note_by_pitch(note_events: list[dict[str, Any]], pitch_midi: int) -> dict[str, Any] | None:
    return next((note for note in note_events if note.get("pitch_midi") == pitch_midi), None)


def melodic_contour(note_events: list[dict[str, Any]]) -> str:
    pitches = [note["pitch_midi"] for note in note_events if note["pitch_midi"] > 0]
    if len(pitches) < 2:
        return "unknown"
    if pitches[-1] > pitches[0]:
        return "rising"
    if pitches[-1] < pitches[0]:
        return "falling"
    return "static"


def median_beat_duration(beats: list[dict[str, Any]]) -> float:
    times = [float(beat.get("time", 0.0) or 0.0) for beat in beats]
    gaps = [current - previous for previous, current in zip(times, times[1:]) if current > previous]
    return round(float(median(gaps)), 3) if gaps else 0.5


def _duration_bucket(duration_s: float, beat_duration: float) -> str:
    if duration_s >= beat_duration * 1.5:
        return "long"
    if duration_s >= beat_duration * 0.75:
        return "mid"
    return "short"


def _lowest_voice(note_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[float, dict[str, Any]] = {}
    for note in note_events:
        key = float(note.get("start_s", 0.0) or 0.0)
        if key not in grouped or int(note.get("pitch_midi", 0) or 0) < int(grouped[key].get("pitch_midi", 0) or 0):
            grouped[key] = note
    return [grouped[key] for key in sorted(grouped)]


def _phrase_windows(section: dict[str, Any], beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    downbeats = [beat for beat in beats if int(beat.get("beat", 0) or 0) == 1 and section["start_s"] <= float(beat.get("time", 0.0) or 0.0) < section["end_s"]]
    anchors = [section["start_s"], *[float(beat.get("time", 0.0) or 0.0) for index, beat in enumerate(downbeats, start=1) if index % 4 == 0], section["end_s"]]
    anchors = sorted(set(round(value, 3) for value in anchors))
    return [{"start_s": anchors[index], "end_s": anchors[index + 1]} for index in range(len(anchors) - 1) if anchors[index + 1] > anchors[index]] or [{"start_s": section["start_s"], "end_s": section["end_s"]}]