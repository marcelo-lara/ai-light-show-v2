from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.song_meta import load_json_file

PARTS = ("vocals", "drums", "bass", "other")


def _load_part_loudness(meta_dir: Path, part: str) -> tuple[np.ndarray, np.ndarray]:
    path = meta_dir / "essentia" / f"loudness_envelope.{part}.json"
    if not path.exists():
        path = meta_dir / "essentia" / f"{part}_loudness_envelope.json"
    if not path.exists():
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    times = np.asarray(payload.get("times") or [], dtype=float)
    loudness = np.asarray(payload.get("loudness") or [], dtype=float)
    if times.size != loudness.size:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    return times, loudness


def build_stem_beat_profiles(meta_dir: Path, beats: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    profiles: dict[str, list[dict[str, Any]]] = {}
    for part in PARTS:
        times, loudness = _load_part_loudness(meta_dir, part)
        rows: list[dict[str, Any]] = []
        if not times.size:
            profiles[part] = rows
            continue
        for index, beat in enumerate(beats[:-1]):
            start_s = float(beat.get("time", 0.0))
            end_s = float(beats[index + 1].get("time", start_s))
            mask = (times >= start_s) & (times < end_s)
            values = loudness[mask]
            window_times = times[mask]
            if not values.size:
                continue
            peak_index = int(np.argmax(values))
            rows.append(
                {
                    "time": start_s,
                    "end_s": end_s,
                    "bar": beat.get("bar"),
                    "beat": beat.get("beat"),
                    "mean": float(np.mean(values)),
                    "min": float(np.min(values)),
                    "peak_time": float(window_times[peak_index]),
                    "peak_value": float(values[peak_index]),
                }
            )
        profiles[part] = rows
    return profiles


def summarize_stem_accents(
    profiles: dict[str, list[dict[str, Any]]],
    start_s: float,
    end_s: float,
    *,
    max_per_part: int = 6,
) -> list[dict[str, Any]]:
    accents: list[dict[str, Any]] = []
    for part, rows in profiles.items():
        section_rows = [row for row in rows if start_s <= float(row["time"]) < end_s]
        if not section_rows:
            continue
        mean_values = np.asarray([float(row["mean"]) for row in section_rows], dtype=float)
        positive_values = mean_values[mean_values > 0.01]
        if not positive_values.size:
            continue
        threshold = max(float(np.percentile(positive_values, 70)), float(np.max(positive_values) * 0.6), 0.05)
        selected = [row for row in section_rows if float(row["mean"]) >= threshold]
        if not selected:
            continue
        accents.append(
            {
                "part": part,
                "threshold": threshold,
                "accents": selected[:max_per_part],
            }
        )
    return accents


def summarize_stem_dips(
    profiles: dict[str, list[dict[str, Any]]],
    start_s: float,
    end_s: float,
    *,
    max_per_part: int = 4,
) -> list[dict[str, Any]]:
    dips: list[dict[str, Any]] = []
    for part, rows in profiles.items():
        section_rows = [row for row in rows if start_s <= float(row["time"]) < end_s]
        if len(section_rows) < 3:
            continue
        mean_values = np.asarray([float(row["mean"]) for row in section_rows], dtype=float)
        positive_values = mean_values[mean_values > 0.01]
        if not positive_values.size:
            continue
        floor_threshold = max(float(np.percentile(positive_values, 35)) * 0.5, 0.02)
        candidates: list[dict[str, Any]] = []
        for index, row in enumerate(section_rows):
            neighbor_values = []
            if index > 0:
                neighbor_values.append(float(section_rows[index - 1]["mean"]))
            if index + 1 < len(section_rows):
                neighbor_values.append(float(section_rows[index + 1]["mean"]))
            if not neighbor_values:
                continue
            neighbor_mean = float(np.mean(neighbor_values))
            if neighbor_mean <= 0.0:
                continue
            mean_ratio = float(row["mean"]) / neighbor_mean
            is_dip = mean_ratio <= 0.75 or (float(row["min"]) <= floor_threshold and mean_ratio <= 0.95)
            if is_dip:
                candidates.append(
                    {
                        "start_s": float(row["time"]),
                        "end_s": float(row["end_s"]),
                        "mean": float(row["mean"]),
                        "min": float(row["min"]),
                        "neighbor_mean": neighbor_mean,
                        "mean_ratio": mean_ratio,
                    }
                )
        if not candidates:
            continue
        merged: list[dict[str, Any]] = []
        current = dict(candidates[0])
        for row in candidates[1:]:
            if abs(float(row["start_s"]) - float(current["end_s"])) < 0.02:
                current["end_s"] = float(row["end_s"])
                current["mean"] = min(float(current["mean"]), float(row["mean"]))
                current["min"] = min(float(current["min"]), float(row["min"]))
                current["neighbor_mean"] = min(float(current["neighbor_mean"]), float(row["neighbor_mean"]))
                current["mean_ratio"] = min(float(current["mean_ratio"]), float(row["mean_ratio"]))
                continue
            merged.append(current)
            current = dict(row)
        merged.append(current)
        merged.sort(key=lambda row: (float(row["mean_ratio"]), float(row["start_s"])))
        dips.append(
            {
                "part": part,
                "dips": merged[:max_per_part],
            }
        )
    return dips


def merge_low_windows(
    stem_dips: list[dict[str, Any]],
    *,
    max_windows: int = 4,
) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    for entry in stem_dips:
        if not isinstance(entry, dict):
            continue
        part = entry.get("part")
        dips = entry.get("dips") if isinstance(entry.get("dips"), list) else []
        if not isinstance(part, str):
            continue
        for dip in dips:
            if not isinstance(dip, dict):
                continue
            start_s = float(dip.get("start_s", 0.0))
            end_s = float(dip.get("end_s", start_s))
            windows.append(
                {
                    "start_s": start_s,
                    "end_s": end_s,
                    "parts": {part},
                    "mean_ratio": float(dip.get("mean_ratio", 1.0)),
                }
            )
    if not windows:
        return []

    windows.sort(key=lambda row: (float(row["start_s"]), float(row["end_s"])))
    durations = [float(row["end_s"]) - float(row["start_s"]) for row in windows if float(row["end_s"]) > float(row["start_s"])]
    merge_gap = max(float(np.median(durations)) if durations else 0.0, 0.02)
    overlap_groups: list[dict[str, Any]] = []
    current = dict(windows[0])
    current["parts"] = set(current["parts"])
    for row in windows[1:]:
        if float(row["start_s"]) < float(current["end_s"]) - 1e-6:
            current["end_s"] = max(float(current["end_s"]), float(row["end_s"]))
            current["parts"].update(row["parts"])
            current["mean_ratio"] = min(float(current["mean_ratio"]), float(row["mean_ratio"]))
            continue
        overlap_groups.append(current)
        current = dict(row)
        current["parts"] = set(current["parts"])
    overlap_groups.append(current)

    merged: list[dict[str, Any]] = []
    index = 0
    while index < len(overlap_groups):
        row = overlap_groups[index]
        if len(row["parts"]) < 2:
            index += 1
            continue
        current = dict(row)
        current["parts"] = set(current["parts"])
        lookahead = index + 1
        while lookahead < len(overlap_groups):
            next_row = overlap_groups[lookahead]
            gap = float(next_row["start_s"]) - float(current["end_s"])
            if gap > merge_gap:
                break
            current["end_s"] = max(float(current["end_s"]), float(next_row["end_s"]))
            current["parts"].update(next_row["parts"])
            current["mean_ratio"] = min(float(current["mean_ratio"]), float(next_row["mean_ratio"]))
            lookahead += 1
        merged.append(current)
        index = lookahead

    merged.sort(
        key=lambda row: (
            -len(row["parts"]),
            -(float(row["end_s"]) - float(row["start_s"])),
            float(row["mean_ratio"]),
            float(row["start_s"]),
        )
    )
    return [
        {
            "start_s": float(row["start_s"]),
            "end_s": float(row["end_s"]),
            "parts": sorted(str(part) for part in row["parts"]),
            "mean_ratio": float(row["mean_ratio"]),
        }
        for row in merged[:max_windows]
    ]