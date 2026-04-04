from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.storage.song_meta import load_json_file

PARTS = ("bass", "drums", "vocals", "other")
PROFILE_BINS = 24
MIN_SIMILARITY = 0.8
MAX_SIGNAL_PATTERNS_PER_PART = 4


def build_stem_patterns(meta_dir: Path, chord_patterns: dict[str, Any] | None = None) -> dict[str, Any] | None:
    payloads = {part: _load_part_payload(meta_dir, part) for part in PARTS}
    if not any(item is not None for item in payloads.values()):
        return None
    stem_patterns = _patterns_from_chord_patterns(payloads, chord_patterns)
    alignment = "chord_patterns"
    if not stem_patterns:
        stem_patterns = _patterns_from_signal_windows(payloads)
        alignment = "signal_windows"
    if not stem_patterns:
        return None
    payload: dict[str, Any] = {
        "pattern_count": len(stem_patterns),
        "settings": {"profile_bins": PROFILE_BINS, "alignment": alignment, "min_similarity": MIN_SIMILARITY},
        "patterns": stem_patterns,
    }
    if alignment == "chord_patterns":
        payload["chord_patterns_file"] = str(meta_dir / "chord_patterns.json")
    return payload


def _patterns_from_chord_patterns(payloads: dict[str, dict[str, np.ndarray] | None], chord_patterns: dict[str, Any] | None) -> list[dict[str, Any]]:
    patterns = chord_patterns.get("patterns") if isinstance(chord_patterns, dict) else None
    if not isinstance(patterns, list) or not patterns:
        return []
    stem_patterns: list[dict[str, Any]] = []
    for chord_pattern in patterns:
        if not isinstance(chord_pattern, dict):
            continue
        occurrences = chord_pattern.get("occurrences") if isinstance(chord_pattern.get("occurrences"), list) else []
        if len(occurrences) < 2:
            continue
        parts_payload: dict[str, Any] = {}
        enriched_occurrences: list[dict[str, Any]] = []
        for occurrence in occurrences:
            if not isinstance(occurrence, dict):
                continue
            start_s = float(occurrence.get("start_time", 0.0))
            end_s = float(occurrence.get("end_time", start_s))
            if end_s <= start_s:
                continue
            occurrence_parts: dict[str, Any] = {}
            for part, part_payload in payloads.items():
                if part_payload is None:
                    continue
                profile = _window_profile(part_payload, start_s, end_s)
                if profile is None:
                    continue
                occurrence_parts[part] = profile
            if occurrence_parts:
                enriched_occurrences.append({**occurrence, "parts": occurrence_parts})
        if len(enriched_occurrences) < 2:
            continue
        for part in PARTS:
            part_occurrences = [item["parts"][part] for item in enriched_occurrences if part in item.get("parts", {})]
            if len(part_occurrences) < 2:
                continue
            representative = _representative_profile(part_occurrences)
            similarities = [_similarity(entry, representative) for entry in part_occurrences]
            parts_payload[part] = {
                "occurrence_count": len(part_occurrences),
                "bins": PROFILE_BINS,
                "loudness_profile": representative["loudness_profile"],
                "envelope_profile": representative["envelope_profile"],
                "mean_loudness": round(float(np.mean([item["mean_loudness"] for item in part_occurrences])), 3),
                "peak_loudness": round(float(np.max([item["peak_loudness"] for item in part_occurrences])), 3),
                "mean_envelope": round(float(np.mean([item["mean_envelope"] for item in part_occurrences])), 3),
                "peak_envelope": round(float(np.max([item["peak_envelope"] for item in part_occurrences])), 3),
                "mean_similarity": round(float(np.mean(similarities)), 3),
            }
            for occurrence, similarity in zip(enriched_occurrences, similarities):
                occurrence["parts"][part] = {**occurrence["parts"][part], "similarity": round(float(similarity), 3)}
        if parts_payload:
            stem_patterns.append(
                {
                    "id": chord_pattern.get("id"),
                    "label": chord_pattern.get("label"),
                    "source": "chord_pattern",
                    "chord_sequence": chord_pattern.get("sequence"),
                    "bar_count": chord_pattern.get("bar_count"),
                    "occurrence_count": len(enriched_occurrences),
                    "parts": parts_payload,
                    "occurrences": enriched_occurrences,
                }
            )
    return stem_patterns


def _patterns_from_signal_windows(payloads: dict[str, dict[str, np.ndarray] | None]) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    for part in PARTS:
        payload = payloads.get(part)
        if payload is None:
            continue
        patterns.extend(_discover_part_patterns(part, payload))
    return patterns


def _load_part_payload(meta_dir: Path, part: str) -> dict[str, np.ndarray] | None:
    path = meta_dir / "essentia" / f"{part}_loudness_envelope.json"
    if not path.exists():
        return None
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        return None
    times = np.asarray(payload.get("times") or [], dtype=float)
    loudness = np.asarray(payload.get("loudness") or [], dtype=float)
    envelope = _coerce_series(payload.get("envelope") or [])
    if not times.size or times.size != loudness.size or times.size != envelope.size:
        return None
    return {"times": times, "loudness": loudness, "envelope": envelope}


def _coerce_series(values: Any) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim == 0:
        return np.asarray([], dtype=float)
    if array.ndim == 1:
        return array
    if array.ndim == 2:
        if 1 in array.shape:
            return array.reshape(-1)
        return np.mean(array, axis=1)
    return array.reshape(-1)


def _window_profile(payload: dict[str, np.ndarray], start_s: float, end_s: float) -> dict[str, Any] | None:
    times = payload["times"]
    loudness = payload["loudness"]
    envelope = payload["envelope"]
    mask = (times >= start_s) & (times <= end_s)
    if int(np.count_nonzero(mask)) < 2:
        return None
    window_times = times[mask]
    normalized_time = (window_times - start_s) / max(end_s - start_s, 1e-6)
    grid = np.linspace(0.0, 1.0, PROFILE_BINS)
    loudness_profile = np.interp(grid, normalized_time, loudness[mask])
    envelope_profile = np.interp(grid, normalized_time, envelope[mask])
    return {
        "start_time": round(start_s, 3),
        "end_time": round(end_s, 3),
        "mean_loudness": round(float(np.mean(loudness_profile)), 3),
        "peak_loudness": round(float(np.max(loudness_profile)), 3),
        "mean_envelope": round(float(np.mean(envelope_profile)), 3),
        "peak_envelope": round(float(np.max(envelope_profile)), 3),
        "loudness_profile": _normalize_profile(loudness_profile),
        "envelope_profile": _normalize_profile(envelope_profile),
    }


def _normalize_profile(values: np.ndarray) -> list[float]:
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    if maximum - minimum < 1e-6:
        return [0.0 for _ in values]
    return [round(float((value - minimum) / (maximum - minimum)), 3) for value in values]


def _representative_profile(occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    loudness = np.median(np.asarray([item["loudness_profile"] for item in occurrences], dtype=float), axis=0)
    envelope = np.median(np.asarray([item["envelope_profile"] for item in occurrences], dtype=float), axis=0)
    return {"loudness_profile": [round(float(value), 3) for value in loudness], "envelope_profile": [round(float(value), 3) for value in envelope]}


def _similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    loudness_error = np.mean(np.abs(np.asarray(left["loudness_profile"], dtype=float) - np.asarray(right["loudness_profile"], dtype=float)))
    envelope_error = np.mean(np.abs(np.asarray(left["envelope_profile"], dtype=float) - np.asarray(right["envelope_profile"], dtype=float)))
    return max(0.0, 1.0 - float((loudness_error + envelope_error) / 2.0))


def _discover_part_patterns(part: str, payload: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    total_duration = float(payload["times"][-1]) if payload["times"].size else 0.0
    if total_duration < 4.0:
        return []
    occupied: list[tuple[float, float]] = []
    patterns: list[dict[str, Any]] = []
    for duration_s in _candidate_durations(total_duration):
        if len(patterns) >= MAX_SIGNAL_PATTERNS_PER_PART:
            break
        candidate = _best_signal_candidate(payload, occupied, duration_s)
        if candidate is None:
            continue
        occupied.extend((float(item["start_time"]), float(item["end_time"])) for item in candidate["occurrences"])
        patterns.append(
            {
                "id": f"{part}_pattern_{chr(ord('A') + len(patterns))}",
                "label": chr(ord("A") + len(patterns)),
                "source": "signal_window",
                "part": part,
                "duration_s": round(duration_s, 3),
                "occurrence_count": len(candidate["occurrences"]),
                "parts": {
                    part: {
                        "occurrence_count": len(candidate["occurrences"]),
                        "bins": PROFILE_BINS,
                        "loudness_profile": candidate["representative"]["loudness_profile"],
                        "envelope_profile": candidate["representative"]["envelope_profile"],
                        "mean_loudness": round(float(np.mean([item["mean_loudness"] for item in candidate["occurrences"]])), 3),
                        "peak_loudness": round(float(np.max([item["peak_loudness"] for item in candidate["occurrences"]])), 3),
                        "mean_envelope": round(float(np.mean([item["mean_envelope"] for item in candidate["occurrences"]])), 3),
                        "peak_envelope": round(float(np.max([item["peak_envelope"] for item in candidate["occurrences"]])), 3),
                        "mean_similarity": round(float(np.mean([item["similarity"] for item in candidate["occurrences"]])), 3),
                    }
                },
                "occurrences": [
                    {
                        "start_time": item["start_time"],
                        "end_time": item["end_time"],
                        "parts": {
                            part: {
                                "similarity": item["similarity"],
                                "loudness_profile": item["loudness_profile"],
                                "envelope_profile": item["envelope_profile"],
                                "mean_loudness": item["mean_loudness"],
                                "peak_loudness": item["peak_loudness"],
                                "mean_envelope": item["mean_envelope"],
                                "peak_envelope": item["peak_envelope"],
                            }
                        },
                    }
                    for item in candidate["occurrences"]
                ],
            }
        )
    return patterns


def _candidate_durations(total_duration: float) -> list[float]:
    base = [8.0, 4.0, 12.0, 16.0, 6.0, 2.0]
    return [duration for duration in base if duration * 2 <= total_duration + 1e-6]


def _best_signal_candidate(payload: dict[str, np.ndarray], occupied: list[tuple[float, float]], duration_s: float) -> dict[str, Any] | None:
    step = max(duration_s / 2.0, 1.0)
    max_start = float(payload["times"][-1]) - duration_s
    best: dict[str, Any] | None = None
    start_s = 0.0
    while start_s <= max_start + 1e-6:
        end_s = start_s + duration_s
        if _window_overlaps(occupied, start_s, end_s):
            start_s += step
            continue
        base = _window_profile(payload, start_s, end_s)
        if base is None:
            start_s += step
            continue
        occurrences = [{**base, "similarity": 1.0}]
        compare_start = start_s + duration_s
        while compare_start <= max_start + 1e-6:
            compare_end = compare_start + duration_s
            if _window_overlaps(occupied, compare_start, compare_end):
                compare_start += step
                continue
            candidate = _window_profile(payload, compare_start, compare_end)
            if candidate is None:
                compare_start += step
                continue
            similarity = round(float(_similarity(candidate, base)), 3)
            if similarity >= MIN_SIMILARITY:
                occurrences.append({**candidate, "similarity": similarity})
                compare_start += duration_s
                continue
            compare_start += step
        if len(occurrences) >= 2:
            score = len(occurrences) * duration_s + float(np.mean([item["similarity"] for item in occurrences]))
            representative = _representative_profile(occurrences)
            candidate_payload = {"occurrences": occurrences, "representative": representative, "score": score}
            if best is None or candidate_payload["score"] > best["score"]:
                best = candidate_payload
        start_s += step
    return best


def _window_overlaps(occupied: list[tuple[float, float]], start_s: float, end_s: float) -> bool:
    for occupied_start, occupied_end in occupied:
        if start_s < occupied_end - 1e-6 and end_s > occupied_start + 1e-6:
            return True
    return False