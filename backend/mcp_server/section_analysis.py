from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.song.artifacts import get_essentia_artifact_entry

PARTS = ("mix", "bass", "drums", "vocals")


def build_section_analysis(song, meta_root: Path, details: dict[str, Any]) -> list[dict[str, Any]]:
    authored = list(getattr(getattr(song, "sections", None), "sections", []) or [])
    authored_by_range = {
        (round(float(item.get("start_s", item.get("start", 0.0)) or 0.0), 3), round(float(item.get("end_s", item.get("end", 0.0)) or 0.0), 3)): item
        for item in authored
        if isinstance(item, dict)
    }
    part_payloads = {part: _load_part_payload(song, meta_root, part) for part in PARTS}
    hints = _load_hints(song, meta_root)
    chords, source = _load_chords(song, meta_root, details)
    analyses: list[dict[str, Any]] = []
    for section in details.get("sections") or []:
        start_s = float(section.get("start_s", 0.0) or 0.0)
        end_s = float(section.get("end_s", start_s) or start_s)
        entry = dict(section)
        authored_section = authored_by_range.get((round(start_s, 3), round(end_s, 3)), {})
        if authored_section.get("description"):
            entry["description"] = str(authored_section.get("description"))
        if isinstance(authored_section.get("hints"), list):
            entry["hints"] = authored_section.get("hints")
        entry["loudness"] = _window_stats(part_payloads.get("mix") or {}, start_s, end_s)
        events = _section_events(hints, start_s, end_s)
        entry["events"] = [event for event in events if "time_s" in event]
        entry["sustained_high_windows"] = [event for event in events if "start_s" in event]
        entry["parts"] = {
            part: _window_stats(payload, start_s, end_s)
            for part, payload in part_payloads.items()
            if payload
        }
        entry["harmony"] = _section_harmony(chords, source, start_s, end_s)
        analyses.append(entry)
    return analyses


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _meta_file_path(meta_root: Path, raw_path: str, song_id: str) -> Path:
    if raw_path.startswith("/app/meta/"):
        return meta_root / raw_path[len("/app/meta/"):]
    return Path(raw_path) if raw_path else meta_root / song_id


def _load_part_payload(song, meta_root: Path, part: str) -> dict[str, Any]:
    entry = get_essentia_artifact_entry(getattr(song.meta, "artifacts", {}) or {}, part, "loudness_envelope") or {}
    path = _meta_file_path(meta_root, str(entry.get("json") or ""), song.song_id)
    payload = _load_json(path)
    return payload if isinstance(payload, dict) else {}


def _load_hints(song, meta_root: Path) -> list[dict[str, Any]]:
    artifacts = getattr(song.meta, "artifacts", {}) or {}
    path = _meta_file_path(meta_root, str(artifacts.get("hints_file") or ""), song.song_id) if isinstance(artifacts, dict) else meta_root / song.song_id / "hints.json"
    if not path.name:
        path = meta_root / song.song_id / "hints.json"
    payload = _load_json(path if path.suffix else meta_root / song.song_id / "hints.json")
    return payload if isinstance(payload, list) else []


def _normalize_chord_label(value: Any) -> str:
    label = str(value or "").strip()
    if not label:
        return ""
    if label in {"N", "None", "none"}:
        return "N"
    replacements = {
        ":min": "m",
        ":maj": "",
        ":dim": "dim",
        ":aug": "aug",
        "min": "m",
        "maj": "",
    }
    for source, target in replacements.items():
        label = label.replace(source, target)
    return label


def _load_chords(song, meta_root: Path, details: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    artifacts = getattr(song.meta, "artifacts", {}) or {}
    raw_path = str(artifacts.get("chords_file") or "") if isinstance(artifacts, dict) else ""
    path = _meta_file_path(meta_root, raw_path, song.song_id) if raw_path else meta_root / song.song_id / "moises" / "chords.json"
    payload = _load_json(path)
    if isinstance(payload, list):
        rows = []
        previous = None
        for row in payload:
            if not isinstance(row, dict):
                continue
            label = _normalize_chord_label(row.get("chord_simple_pop") or row.get("chord_basic_pop") or row.get("prev_chord"))
            if not label or label == previous:
                continue
            rows.append({"time_s": float(row.get("curr_beat_time", 0.0) or 0.0), "bar": int(row.get("bar_num", 0) or 0), "beat": int(row.get("beat_num", 0) or 0), "label": label})
            previous = label
        if rows:
            return rows, "moises"
    return list((details.get("analysis") or {}).get("chords") or []), "beats"


def _window_stats(payload: dict[str, Any], start_s: float, end_s: float) -> dict[str, Any]:
    times = [float(value) for value in payload.get("times") or []]
    loudness = [float(value) for value in payload.get("loudness") or []]
    values = [(time_s, value) for time_s, value in zip(times, loudness) if start_s <= time_s <= end_s]
    if not values:
        return {}
    peak = max(values, key=lambda item: item[1])
    valley = min(values, key=lambda item: item[1])
    only_values = [item[1] for item in values]
    return {
        "average": round(sum(only_values) / len(only_values), 6),
        "minimum": round(valley[1], 6),
        "maximum": round(peak[1], 6),
        "peak_time_s": round(peak[0], 3),
        "valley_time_s": round(valley[0], 3),
        "samples": len(values),
    }


def _section_events(hints: list[dict[str, Any]], start_s: float, end_s: float) -> list[dict[str, Any]]:
    for section in hints:
        if round(float(section.get("start_s", 0.0) or 0.0), 3) != round(start_s, 3):
            continue
        if round(float(section.get("end_s", 0.0) or 0.0), 3) != round(end_s, 3):
            continue
        kept = []
        for hint in section.get("hints") or []:
            if not isinstance(hint, dict):
                continue
            parts = [part for part in (hint.get("parts") or []) if part in PARTS]
            dominant = hint.get("dominant_part")
            if dominant not in PARTS:
                dominant = parts[0] if parts else "mix"
            kept.append({key: value for key, value in hint.items() if key in {"time_s", "start_s", "end_s", "kind", "strength"}} | {"dominant_part": dominant, "parts": parts or ["mix"]})
        return kept
    return []


def _section_harmony(chords: list[dict[str, Any]], source: str, start_s: float, end_s: float) -> dict[str, Any]:
    if not chords:
        return {"source": source, "change_count": 0, "change_density": 0.0, "chord_changes": [], "chord_spans": [], "dominant_chords": [], "repeating_patterns": []}
    section_rows = [row for row in chords if start_s <= float(row.get("time_s", 0.0) or 0.0) < end_s]
    previous = next((row for row in reversed(chords) if float(row.get("time_s", 0.0) or 0.0) < start_s), None)
    timeline = ([previous] if previous is not None else []) + section_rows
    if not timeline:
        return {"source": source, "change_count": 0, "change_density": 0.0, "chord_changes": [], "chord_spans": [], "dominant_chords": [], "repeating_patterns": []}
    spans = []
    totals: dict[str, float] = {}
    for index, row in enumerate(timeline):
        span_start = max(start_s, float(row.get("time_s", 0.0) or 0.0))
        next_time = float(timeline[index + 1].get("time_s", end_s) or end_s) if index + 1 < len(timeline) else end_s
        span_end = min(end_s, next_time)
        if span_end <= span_start:
            continue
        label = str(row.get("label") or row.get("chord") or "")
        spans.append({"start_s": round(span_start, 3), "end_s": round(span_end, 3), "label": label})
        totals[label] = totals.get(label, 0.0) + (span_end - span_start)
    labels = [str(row.get("label") or row.get("chord") or "") for row in section_rows if str(row.get("label") or row.get("chord") or "")]
    return {
        "source": source,
        "change_count": len(section_rows),
        "change_density": round(len(section_rows) / max(end_s - start_s, 0.001), 6),
        "chord_changes": [{"time_s": round(float(row.get("time_s", 0.0) or 0.0), 3), "bar": row.get("bar"), "beat": row.get("beat"), "label": str(row.get("label") or row.get("chord") or "")} for row in section_rows[:16]],
        "chord_spans": spans[:12],
        "dominant_chords": [{"label": label, "duration_s": round(duration, 3)} for label, duration in sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:4]],
        "repeating_patterns": _find_patterns(labels),
    }


def _find_patterns(labels: list[str]) -> list[list[str]]:
    filtered = [label for label in labels if label and label != "N"]
    for size in range(2, min(5, len(filtered) // 2 + 1)):
        pattern = filtered[:size]
        if pattern and filtered[: size * 2] == pattern * 2:
            return [pattern]
    return []
