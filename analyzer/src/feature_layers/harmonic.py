from __future__ import annotations

from pathlib import Path
from typing import Any

from .harmonic_support import average_profile, cadence_note, chord_confidence, dominant_pitch_classes, harmonic_role, key_stability_label, profile_clarity, progression, tension_level, tension_score
from ..storage.song_meta import canonical_beats_path, load_json_file, load_sections


def build_harmonic_layer(song_path: Path, meta_path: Path) -> dict[str, Any]:
    beats_file = canonical_beats_path(song_path, meta_path)
    beats_rows = load_json_file(beats_file) if beats_file.exists() else []
    beats = [row for row in beats_rows if isinstance(row, dict)]
    meta_dir = meta_path / song_path.stem
    info = load_json_file(meta_dir / "info.json") if (meta_dir / "info.json").exists() else {}
    features = load_json_file(meta_dir / "features.json") if (meta_dir / "features.json").exists() else {}
    patterns = load_json_file(meta_dir / "chord_patterns.json") if (meta_dir / "chord_patterns.json").exists() else None
    sections = load_sections(meta_dir)
    key_label = _key_label(info, features)
    hpcp_payload, hpcp_path = _hpcp_payload(meta_dir)
    hpcp_times = [float(value) for value in (hpcp_payload.get("times") or [])]
    hpcp_rows = [row for row in (hpcp_payload.get("hpcp") or []) if isinstance(row, list) and row]
    chord_events = _build_chord_events(beats, sections, hpcp_times, hpcp_rows, key_label)
    section_harmony = [_section_harmony(section, chord_events, hpcp_times, hpcp_rows, key_label) for section in sections]
    cadence_notes = [item["cadence"] for item in section_harmony if isinstance(item.get("cadence"), dict)]
    global_profile = average_profile(hpcp_times, hpcp_rows)
    clarity = profile_clarity(global_profile)
    harmonic_progression = progression(chord_events)
    tension_peaks = sorted([entry for entry in section_harmony if entry.get("tension_level") in {"medium", "high"}], key=lambda item: float(item.get("tension_score", 0.0) or 0.0), reverse=True)
    return {
        "schema_version": "1.0",
        "song_id": song_path.stem,
        "generated_from": {
            "beats_file": str(beats_file),
            "info_file": str(meta_dir / "info.json"),
            "features_file": str(meta_dir / "features.json"),
            "chord_patterns_file": str(meta_dir / "chord_patterns.json"),
            "hpcp_file": str(hpcp_path),
        },
        "global_key": {
            "label": key_label,
            "confidence": round(
                max(
                    float(((((features.get("global") or {}).get("key") or {}).get("detected") or {}).get("strength") or 0.0)),
                    clarity,
                ),
                3,
            ),
            "source": "info.song_key+hpcp",
        },
        "harmonic_summary": {
            "progression": harmonic_progression,
            "key_stability": key_stability_label(clarity, len(cadence_notes)),
            "cadence_notes": cadence_notes,
            "tension_profile": _tension_profile(tension_peaks),
            "dominant_pitch_classes": dominant_pitch_classes(global_profile),
            "harmonic_clarity": clarity,
            "harmonic_mobility": round(len(chord_events) / max(len({event.get('bar') for event in chord_events if event.get('bar')}), 1), 3) if chord_events else 0.0,
        },
        "chord_events": chord_events,
        "chord_patterns": patterns if isinstance(patterns, dict) else {"pattern_count": 0, "patterns": []},
        "section_harmony": section_harmony,
        "tension_peaks": tension_peaks,
        "validation_notes": _validation_notes(chord_events, hpcp_rows),
    }


def _build_chord_events(beats: list[dict[str, Any]], sections: list[dict[str, Any]], hpcp_times: list[float], hpcp_rows: list[list[float]], key_label: str) -> list[dict[str, Any]]:
    rows = [row for row in beats if str(row.get("chord") or "").strip()]
    if not rows:
        return []
    events: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        chord_label = str(row.get("chord") or "")
        if events and events[-1]["chord"] == chord_label:
            events[-1]["duration_beats"] += 1
            events[-1]["end_s"] = round(float(row.get("time", events[-1]["end_s"]) or events[-1]["end_s"]), 3)
            continue
        time_value = round(float(row.get("time", 0.0) or 0.0), 3)
        next_time = round(float(rows[index + 1].get("time", time_value) or time_value), 3) if index + 1 < len(rows) else time_value
        section_name = _section_name(time_value, sections)
        profile = average_profile(hpcp_times, hpcp_rows, time_value, next_time if next_time > time_value else None)
        events.append(
            {
                "time": time_value,
                "end_s": next_time,
                "bar": int(row.get("bar", 0) or 0),
                "beat": int(row.get("beat", 0) or 0),
                "chord": chord_label,
                "bass": row.get("bass"),
                "duration_beats": 1,
                "section_name": section_name,
                "confidence": chord_confidence(profile, chord_label),
                "harmonic_role": harmonic_role(chord_label, key_label),
            }
        )
    return events


def _hpcp_payload(meta_dir: Path) -> tuple[dict[str, Any], Path]:
    for path in (meta_dir / "essentia" / "other_chroma_hpcp.json", meta_dir / "essentia" / "chroma_hpcp.json"):
        if path.exists():
            payload = load_json_file(path)
            return (payload if isinstance(payload, dict) else {}), path
    return {}, meta_dir / "essentia" / "chroma_hpcp.json"


def _key_label(info: dict[str, Any], features: dict[str, Any]) -> str:
    if str(info.get("song_key") or ""):
        return str(info.get("song_key") or "")
    global_payload = (features.get("global") or {}) if isinstance(features.get("global"), dict) else {}
    key_payload = (global_payload.get("key") or {}) if isinstance(global_payload.get("key"), dict) else {}
    canonical = str(key_payload.get("canonical") or "")
    if canonical:
        return canonical
    detected = (key_payload.get("detected") or {}) if isinstance(key_payload.get("detected"), dict) else {}
    detected_key = str(detected.get("key") or "")
    detected_scale = str(detected.get("scale") or "")
    if detected_key and detected_scale:
        return f"{detected_key} {detected_scale}"
    return detected_key


def _section_harmony(section: dict[str, Any], chord_events: list[dict[str, Any]], hpcp_times: list[float], hpcp_rows: list[list[float]], key_label: str) -> dict[str, Any]:
    events = [event for event in chord_events if section["name"] == event.get("section_name")]
    unique = list(dict.fromkeys(event["chord"] for event in events if event.get("chord")))
    bars = max(len({int(event.get("bar", 0) or 0) for event in events if int(event.get("bar", 0) or 0) > 0}), 1)
    change_rate = round(max(len(events) - 1, 0) / bars, 3)
    profile = average_profile(hpcp_times, hpcp_rows, section["start_s"], section["end_s"])
    clarity = profile_clarity(profile)
    cadence = cadence_note(section, events, key_label)
    score = tension_score(section, unique, change_rate, clarity, cadence)
    return {
        "section_id": f"{section['name'].lower().replace(' ', '-')}-{section['start_s']:.2f}",
        "section_name": section["name"],
        "start_s": section["start_s"],
        "end_s": section["end_s"],
        "dominant_chords": unique[:6],
        "harmonic_density": len(unique),
        "chord_change_rate": change_rate,
        "dominant_pitch_classes": dominant_pitch_classes(profile),
        "hpcp_clarity": clarity,
        "cadence": cadence,
        "tension_score": score,
        "tension_level": tension_level(score),
        "summary": _section_summary(section["name"], unique, cadence),
    }


def _section_summary(section_name: str, chords: list[str], cadence: dict[str, Any] | None) -> str:
    if not chords:
        return "No chord summary available."
    cadence_text = f" closes with {cadence['type'].replace('_', ' ')}." if cadence else "."
    return f"{section_name} moves through {' -> '.join(chords[:4])}{cadence_text}"


def _tension_profile(tension_peaks: list[dict[str, Any]]) -> str:
    if not tension_peaks:
        return "Insufficient harmonic detail."
    strongest = tension_peaks[0]
    return f"Tension peaks in {strongest['section_name']} with a {strongest['tension_level']} harmonic load."


def _validation_notes(chord_events: list[dict[str, Any]], hpcp_rows: list[list[float]]) -> list[str]:
    notes: list[str] = []
    if not chord_events:
        notes.append("No chord events available in canonical beats.")
    if not hpcp_rows:
        notes.append("No Essentia HPCP artifact available; harmonic clarity metrics fall back to beat chords only.")
    return notes


def _section_name(time_value: float, sections: list[dict[str, Any]]) -> str:
    for index, section in enumerate(sections):
        is_last = index == len(sections) - 1
        if section["start_s"] <= time_value < section["end_s"] or (is_last and section["start_s"] <= time_value <= section["end_s"]):
            return section["name"]
    return ""