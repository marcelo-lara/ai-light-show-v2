from __future__ import annotations

from typing import Any

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_EQUIVALENTS = {"Bb": "A#", "Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Cb": "B", "Fb": "E"}


def average_profile(times: list[float], hpcp_rows: list[list[float]], start_s: float | None = None, end_s: float | None = None) -> list[float]:
    if not times or not hpcp_rows:
        return []
    selected = [row for time_value, row in zip(times, hpcp_rows) if _matches_window(time_value, start_s, end_s)]
    if not selected and start_s is not None and end_s is not None:
        target = (start_s + end_s) / 2.0
        index = min(range(len(times)), key=lambda item: abs(times[item] - target))
        selected = [hpcp_rows[index]]
    if not selected:
        selected = hpcp_rows
    width = len(selected[0])
    return [round(sum(row[index] for row in selected) / len(selected), 4) for index in range(width)]


def cadence_note(section: dict[str, Any], events: list[dict[str, Any]], key_label: str) -> dict[str, Any] | None:
    unique = [event for event in events if str(event.get("chord") or "") not in {"", "N"}]
    if len(unique) < 2:
        return None
    tonic_pc = pitch_class(key_label)
    final = parse_chord(unique[-1].get("chord"))
    previous = parse_chord(unique[-2].get("chord"))
    if tonic_pc is None or not final or not previous:
        return None
    final_interval = (final["root_pc"] - tonic_pc) % 12
    previous_interval = (previous["root_pc"] - tonic_pc) % 12
    cadence_type = "open_cadence"
    strength = "medium"
    if final_interval == 0:
        cadence_type = "tonic_arrival"
        strength = "gentle"
        if previous_interval == 7:
            cadence_type = "dominant_resolution"
            strength = "strong"
        elif previous_interval == 5:
            cadence_type = "plagal_resolution"
        elif previous_interval in {10, 11}:
            cadence_type = "leading_lift"
    return {
        "section_name": section["name"],
        "time": round(float(unique[-1].get("time", section["end_s"])), 3),
        "type": cadence_type,
        "from_chord": str(unique[-2].get("chord") or ""),
        "to_chord": str(unique[-1].get("chord") or ""),
        "resolution_strength": strength,
    }


def chord_confidence(profile: list[float], chord_label: str) -> float:
    tones = chord_tones(chord_label)
    if not profile or not tones:
        return 0.0
    return round(sum(profile[index] for index in tones) / len(tones), 3)


def chord_tones(chord_label: str) -> list[int]:
    parsed = parse_chord(chord_label)
    if not parsed:
        return []
    root = parsed["root_pc"]
    quality = parsed["quality"]
    third = 3 if quality == "minor" else 4
    fifth = 6 if quality == "diminished" else 8 if quality == "augmented" else 7
    tones = [root, (root + third) % 12, (root + fifth) % 12]
    if parsed["has_seventh"]:
        tones.append((root + (11 if "maj7" in parsed["suffix"] else 10)) % 12)
    return tones


def dominant_pitch_classes(profile: list[float], limit: int = 3) -> list[dict[str, Any]]:
    if not profile:
        return []
    ranking = sorted(range(len(profile)), key=lambda index: profile[index], reverse=True)[:limit]
    return [{"pitch_class": PITCH_CLASSES[index], "weight": round(profile[index], 3)} for index in ranking]


def harmonic_role(chord_label: str, key_label: str) -> str:
    tonic_pc = pitch_class(key_label)
    parsed = parse_chord(chord_label)
    if tonic_pc is None or not parsed:
        return "unknown"
    interval = (parsed["root_pc"] - tonic_pc) % 12
    if interval == 0:
        return "tonic"
    if interval == 7:
        return "dominant"
    if interval == 5:
        return "subdominant"
    if interval in {2, 9}:
        return "predominant"
    return "color"


def key_stability_label(clarity: float, cadence_count: int) -> str:
    if clarity >= 0.18 and cadence_count:
        return "stable"
    if clarity >= 0.1:
        return "centered"
    return "ambiguous"


def parse_chord(chord_label: Any) -> dict[str, Any] | None:
    label = str(chord_label or "").strip().replace("♯", "#").replace("♭", "b")
    if not label or label == "N":
        return None
    root_token = label[:2] if len(label) > 1 and label[1] in {"#", "b"} else label[:1]
    root_pc = pitch_class(root_token)
    if root_pc is None:
        return None
    suffix = label[len(root_token):]
    quality = "minor" if suffix.startswith("m") and not suffix.startswith("maj") else "major"
    if "dim" in suffix:
        quality = "diminished"
    elif "aug" in suffix:
        quality = "augmented"
    return {"root_pc": root_pc, "quality": quality, "suffix": suffix, "has_seventh": "7" in suffix}


def pitch_class(label: Any) -> int | None:
    token = str(label or "").strip().replace("♯", "#").replace("♭", "b")
    if not token:
        return None
    if len(token) > 1 and token[1] in {"#", "b"}:
        token = token[:2]
    else:
        token = token[:1]
    token = FLAT_EQUIVALENTS.get(token, token)
    return PITCH_CLASSES.index(token) if token in PITCH_CLASSES else None


def profile_clarity(profile: list[float]) -> float:
    if len(profile) < 2:
        return 0.0
    ranked = sorted(profile, reverse=True)
    return round(max(ranked[0] - ranked[1], 0.0), 3)


def progression(chord_events: list[dict[str, Any]]) -> list[str]:
    items: list[str] = []
    for event in chord_events:
        chord = str(event.get("chord") or "")
        if chord and chord != "N" and (not items or items[-1] != chord):
            items.append(chord)
    return items[:16]


def tension_score(section: dict[str, Any], unique_chords: list[str], change_rate: float, clarity: float, cadence: dict[str, Any] | None) -> float:
    duration_bars = max((section["end_s"] - section["start_s"]) / 2.0, 1.0)
    density = min(len(unique_chords) / max(duration_bars, 1.0), 1.0)
    mobility = min(change_rate / 1.5, 1.0)
    ambiguity = 1.0 - min(max(clarity, 0.0), 1.0)
    unresolved = 0.0 if (cadence or {}).get("type") in {"dominant_resolution", "plagal_resolution", "tonic_arrival"} else 0.6
    return round(min(1.0, (density * 0.35) + (mobility * 0.35) + (ambiguity * 0.2) + (unresolved * 0.1)), 3)


def tension_level(score: float) -> str:
    if score >= 0.67:
        return "high"
    if score >= 0.34:
        return "medium"
    return "low"


def _matches_window(time_value: float, start_s: float | None, end_s: float | None) -> bool:
    if start_s is not None and time_value < start_s:
        return False
    if end_s is not None and time_value > end_s:
        return False
    return True