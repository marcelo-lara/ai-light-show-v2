from __future__ import annotations

import bisect
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

META_PATH = "/app/meta"
COMPARE_WINDOW_SECONDS = 4.0
COMPARE_STEP_SECONDS = 30.0
COMPARE_CLOSE_THRESHOLD_MS = 60.0
COMPARE_METHOD = "consensus_median_nearest_neighbor"


def warn(message: str) -> None:
    print(f"WARNING: {message}")


def _round_floats(value):
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, dict):
        return {k: _round_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round_floats(v) for v in value]
    if isinstance(value, tuple):
        return [_round_floats(v) for v in value]
    return value


def _dump_json(path: Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_round_floats(payload), f, indent=2)


def _load_json_file(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _song_name(song_path: str | Path) -> str:
    return Path(song_path).expanduser().resolve().stem


def _song_meta_dir(song_path: str | Path, meta_path: str | Path) -> Path:
    return Path(meta_path).expanduser().resolve() / _song_name(song_path)


def _parse_numeric_list(values, source_name: str, emit_warn: bool = True) -> tuple[list[float], int]:
    beats: list[float] = []
    skipped = 0
    for value in values:
        try:
            beats.append(float(value))
        except (TypeError, ValueError):
            skipped += 1
    if skipped and emit_warn:
        warn(f"{source_name}: skipped {skipped} malformed beat entries")
    beats.sort()
    return beats, skipped


def _load_essentia_beats(path: Path) -> tuple[list[float], int]:
    payload = _load_json_file(path)
    rhythm = payload.get("rhythm", {}) if isinstance(payload, dict) else {}
    beats = rhythm.get("beats", []) if isinstance(rhythm, dict) else []
    if not isinstance(beats, list):
        warn(f"Essentia beats payload is not a list: {path}")
        return [], 0
    return _parse_numeric_list(beats, "essentia")


def _load_moises_beats(path: Path) -> tuple[list[float], int]:
    payload = _load_json_file(path)
    if not isinstance(payload, list):
        warn(f"Moises beats payload is not a list: {path}")
        return [], 0

    values = []
    skipped = 0
    for item in payload:
        if not isinstance(item, dict) or "time" not in item:
            skipped += 1
            continue
        values.append(item.get("time"))

    beats, malformed = _parse_numeric_list(values, "moises", emit_warn=False)
    skipped += malformed
    if skipped:
        warn(f"moises: skipped {skipped} malformed beat entries")
    return beats, skipped


def _load_analyzer_beats(path: Path) -> tuple[list[float], int]:
    payload = _load_json_file(path)
    beats = payload.get("beats", []) if isinstance(payload, dict) else []
    if not isinstance(beats, list):
        warn(f"Analyzer beats payload is not a list: {path}")
        return [], 0
    return _parse_numeric_list(beats, "analyzer")


def _beats_in_window(beats: list[float], start_sec: float, window_sec: float) -> list[float]:
    end_sec = start_sec + window_sec
    return [t for t in beats if start_sec <= t < end_sec]


def _nearest_delta_seconds(target_time: float, sorted_reference: list[float]) -> Optional[float]:
    if not sorted_reference:
        return None
    idx = bisect.bisect_left(sorted_reference, target_time)
    candidates = []
    if idx < len(sorted_reference):
        candidates.append(abs(sorted_reference[idx] - target_time))
    if idx > 0:
        candidates.append(abs(sorted_reference[idx - 1] - target_time))
    if not candidates:
        return None
    return min(candidates)


def _window_error_stats(base_beats: list[float], reference_beats: list[float]) -> dict:
    if not base_beats or not reference_beats:
        return {
            "count": len(base_beats),
            "median_error_ms": None,
            "mean_error_ms": None,
            "close": None,
            "computable": False,
        }

    deltas = []
    for beat_time in base_beats:
        delta = _nearest_delta_seconds(beat_time, reference_beats)
        if delta is not None:
            deltas.append(delta)

    if not deltas:
        return {
            "count": len(base_beats),
            "median_error_ms": None,
            "mean_error_ms": None,
            "close": None,
            "computable": False,
        }

    median_error_ms = statistics.median(deltas) * 1000.0
    mean_error_ms = statistics.mean(deltas) * 1000.0
    return {
        "count": len(base_beats),
        "median_error_ms": float(median_error_ms),
        "mean_error_ms": float(mean_error_ms),
        "close": median_error_ms <= COMPARE_CLOSE_THRESHOLD_MS,
        "computable": True,
    }


def run_compare_beat_times_for(song_path: Path, meta_path: str | Path = META_PATH) -> Optional[dict]:
    meta_root = Path(meta_path).expanduser().resolve()
    song_meta_dir = _song_meta_dir(song_path, meta_root)

    essentia_file = song_meta_dir / "essentia" / "rhythm.json"
    moises_file = song_meta_dir / "moises" / "beats.json"
    analyzer_file = song_meta_dir / "beats.json"

    required_files = [essentia_file, moises_file, analyzer_file]
    missing_files = [path for path in required_files if not path.exists()]
    if missing_files:
        for path in missing_files:
            warn(f"Missing required beat source file: {path}")
        return None

    try:
        essentia_beats, _ = _load_essentia_beats(essentia_file)
        moises_beats, _ = _load_moises_beats(moises_file)
        analyzer_beats, _ = _load_analyzer_beats(analyzer_file)
    except Exception as exc:
        warn(f"Failed to load beat sources: {exc}")
        return None

    source_beats = {
        "essentia": essentia_beats,
        "moises": moises_beats,
        "analyzer": analyzer_beats,
    }

    max_time_candidates = [beats[-1] for beats in source_beats.values() if beats]
    if not max_time_candidates:
        warn("No beats available in any source; cannot compare")
        return None

    max_time = max(max_time_candidates)
    window_starts = []
    cursor = 0.0
    while cursor <= max_time:
        window_starts.append(round(cursor, 6))
        cursor += COMPARE_STEP_SECONDS

    windows = []
    per_source_window_medians: dict[str, list[float]] = {name: [] for name in source_beats}

    for start_sec in window_starts:
        end_sec = start_sec + COMPARE_WINDOW_SECONDS
        window_source_beats = {
            name: _beats_in_window(beats, start_sec, COMPARE_WINDOW_SECONDS)
            for name, beats in source_beats.items()
        }

        window_entry = {
            "start_sec": start_sec,
            "end_sec": end_sec,
            "sources": {},
        }

        for source_name in source_beats:
            reference = []
            for other_name, beats in window_source_beats.items():
                if other_name != source_name:
                    reference.extend(beats)
            reference.sort()

            stats = _window_error_stats(window_source_beats[source_name], reference)
            window_entry["sources"][source_name] = stats
            median_ms = stats.get("median_error_ms")
            if median_ms is not None:
                per_source_window_medians[source_name].append(float(median_ms))

        windows.append(window_entry)

    overall = {}
    for source_name, median_values in per_source_window_medians.items():
        if median_values:
            overall[source_name] = {
                "window_count": len(median_values),
                "overall_median_error_ms": float(statistics.median(median_values)),
                "overall_mean_error_ms": float(statistics.mean(median_values)),
                "close_window_count": sum(
                    1
                    for window in windows
                    if window["sources"][source_name].get("close") is True
                ),
            }
        else:
            overall[source_name] = {
                "window_count": 0,
                "overall_median_error_ms": None,
                "overall_mean_error_ms": None,
                "close_window_count": 0,
            }

    ranked_sources = sorted(
        overall.keys(),
        key=lambda name: (
            overall[name]["overall_median_error_ms"] is None,
            overall[name]["overall_median_error_ms"] if overall[name]["overall_median_error_ms"] is not None else float("inf"),
        ),
    )
    winner = None
    if ranked_sources and overall[ranked_sources[0]]["overall_median_error_ms"] is not None:
        winner = ranked_sources[0]

    report = {
        "song": song_path.stem,
        "config": {
            "window_seconds": COMPARE_WINDOW_SECONDS,
            "step_seconds": COMPARE_STEP_SECONDS,
            "close_threshold_ms": COMPARE_CLOSE_THRESHOLD_MS,
            "method": COMPARE_METHOD,
        },
        "sources": {
            "essentia": str(essentia_file),
            "moises": str(moises_file),
            "analyzer": str(analyzer_file),
        },
        "windows": windows,
        "overall": {
            "sources": overall,
            "ranking": ranked_sources,
            "winner": winner,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    report_file = song_meta_dir / "beat_comparison.json"
    _dump_json(report_file, report)

    print("\nBeat Time Comparison")
    print(
        f"Sampling: {COMPARE_WINDOW_SECONDS:.1f}s window every {COMPARE_STEP_SECONDS:.1f}s | "
        f"close <= {COMPARE_CLOSE_THRESHOLD_MS:.1f}ms"
    )
    print("Window        | Essentia       | Moises         | Analyzer")
    print("--------------+----------------+----------------+----------------")
    for window in windows:
        start_sec = window["start_sec"]
        end_sec = window["end_sec"]

        def _fmt(name: str) -> str:
            metrics = window["sources"][name]
            median = metrics.get("median_error_ms")
            if median is None:
                return "n/a"
            close_flag = "Y" if metrics.get("close") else "N"
            return f"{median:6.1f}ms {close_flag}"

        print(
            f"{start_sec:6.1f}-{end_sec:6.1f} | "
            f"{_fmt('essentia'):14} | "
            f"{_fmt('moises'):14} | "
            f"{_fmt('analyzer'):14}"
        )

    print("\nOverall ranking (lower median error is better):")
    for idx, source_name in enumerate(ranked_sources, start=1):
        metric = overall[source_name]["overall_median_error_ms"]
        metric_text = "n/a" if metric is None else f"{metric:.1f}ms"
        print(f"{idx}. {source_name}: {metric_text}")

    if winner is None:
        warn("No computable windows were found; winner is null")
    else:
        print(f"Winner: {winner}")

    print(f"Saved report: {report_file}")
    return report
