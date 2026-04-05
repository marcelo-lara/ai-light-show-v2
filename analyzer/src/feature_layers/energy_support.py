from __future__ import annotations

from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

from ..storage.song_meta import load_json_file


def load_series(meta_dir: Path, file_name: str, value_key: str) -> dict[str, Any]:
    path = meta_dir / "essentia" / file_name
    if not path.exists():
        return {"path": path, "times": [], "values": []}
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        return {"path": path, "times": [], "values": []}
    times = [float(value) for value in (payload.get("times") or [])]
    values = [float(value) for value in (payload.get(value_key) or [])]
    if len(times) != len(values):
        return {"path": path, "times": [], "values": []}
    return {"path": path, "times": times, "values": values}


def load_rhythm(meta_dir: Path) -> dict[str, Any]:
    path = meta_dir / "essentia" / "rhythm.json"
    if not path.exists():
        return {"path": path}
    payload = load_json_file(path)
    return payload if isinstance(payload, dict) else {"path": path}


def onset_summary(rhythm_payload: dict[str, Any], accent_candidates: list[dict[str, Any]], duration_s: float) -> dict[str, Any]:
    onsets = rhythm_payload.get("onsets") if isinstance(rhythm_payload.get("onsets"), dict) else {}
    onset_times = [float(value) for value in (onsets.get("times") or [])]
    onset_rate = [float(value) for value in (onsets.get("rate") or [])]
    beat_loudness = rhythm_payload.get("beat_loudness") if isinstance(rhythm_payload.get("beat_loudness"), dict) else {}
    beat_values = [float(value) for value in (beat_loudness.get("values") or [])]
    windows = merge_hit_windows(onset_times, onset_rate, accent_candidates)
    return {
        "mean_strength": round(_mean(onset_rate), 3),
        "peak_strength": round(max(onset_rate, default=0.0), 3),
        "onset_count": len(onset_times),
        "onset_density_per_minute": round((len(onset_times) / duration_s) * 60.0, 3) if duration_s > 0 else 0.0,
        "beat_loudness_mean": round(_mean(beat_values), 3),
        "beat_loudness_std": round(_std(beat_values), 3),
        "flux_mean": round(_mean(onset_rate), 3),
        "flux_peak": round(max(onset_rate, default=0.0), 3),
        "hit_windows": windows,
    }


def section_series_stats(series: dict[str, Any], start_s: float, end_s: float) -> dict[str, float]:
    values = [value for time_value, value in zip(series.get("times", []), series.get("values", [])) if start_s <= time_value < end_s]
    if not values:
        return {"mean": 0.0, "peak": 0.0, "percentile_90": 0.0, "std": 0.0}
    return {
        "mean": round(_mean(values), 3),
        "peak": round(max(values), 3),
        "percentile_90": round(percentile(values, 0.9), 3),
        "std": round(_std(values), 3),
    }


def spectral_summary(centroid_series: dict[str, Any], onset_profile: dict[str, Any], sections: list[dict[str, Any]]) -> dict[str, Any]:
    centroid_values = list(centroid_series.get("values", []))
    section_means = [section_series_stats(centroid_series, section["start_s"], section["end_s"])["mean"] for section in sections]
    trend = summarize_series_trend(section_means)
    centroid_mean = round(_mean(centroid_values), 3)
    centroid_peak = round(max(centroid_values, default=0.0), 3)
    centroid_std = round(_std(centroid_values), 3)
    return {
        "centroid_mean": centroid_mean,
        "centroid_peak": centroid_peak,
        "centroid_std": centroid_std,
        "centroid_percentile_90": round(percentile(centroid_values, 0.9), 3),
        "centroid_summary": describe_centroid(centroid_mean, centroid_peak, trend),
        "flux_summary": describe_flux(float(onset_profile.get("flux_mean", 0.0) or 0.0), float(onset_profile.get("flux_peak", 0.0) or 0.0), int(onset_profile.get("onset_count", 0) or 0)),
        "brightness_trend": trend,
    }


def loudness_summary(loudness_series: dict[str, Any], accent_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    loudness_values = list(loudness_series.get("values", []))
    return {
        "mean": round(_mean(loudness_values), 3),
        "peak": round(max(loudness_values, default=0.0), 3),
        "percentile_90": round(percentile(loudness_values, 0.9), 3),
        "envelope_variation": round(_std(loudness_values), 3),
        "notable_rises": [item for item in accent_candidates if item["kind"] == "rise"][:12],
        "notable_dips": [item for item in accent_candidates if item["kind"] == "drop"][:12],
    }


def merge_hit_windows(onset_times: list[float], onset_rate: list[float], accent_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    onset_windows = [
        {"time": round(time_value, 3), "kind": "onset", "intensity": round(rate_at_time(onset_rate, onset_times, time_value), 3), "related_parts": [], "section_name": ""}
        for time_value in onset_times
    ]
    strongest_onsets = sorted(onset_windows, key=lambda item: float(item.get("intensity", 0.0) or 0.0), reverse=True)[:8]
    merged = strongest_onsets + accent_candidates[:8]
    return sorted(merged, key=lambda item: float(item.get("time", 0.0) or 0.0))[:16]


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * ratio)))
    return float(ordered[index])


def rate_at_time(rate_values: list[float], onset_times: list[float], target_time: float) -> float:
    if not rate_values:
        return 0.0
    if not onset_times:
        return max(rate_values)
    span = max(onset_times[-1], target_time, 0.001)
    index = min(len(rate_values) - 1, max(0, int((target_time / span) * (len(rate_values) - 1))))
    return float(rate_values[index])


def summarize_series_trend(section_means: list[float]) -> str:
    values = [value for value in section_means if value > 0.0]
    if len(values) < 2:
        return "unknown"
    deltas = [current - previous for previous, current in zip(values, values[1:])]
    if all(abs(delta) <= 0.01 for delta in deltas):
        return "plateau"
    if sum(1 for delta in deltas if delta > 0) >= len(deltas) * 0.7:
        return "rising"
    if sum(1 for delta in deltas if delta < 0) >= len(deltas) * 0.7:
        return "falling"
    return "wave"


def describe_centroid(mean_value: float, peak_value: float, trend: str) -> str:
    brightness = "dark" if mean_value < 0.12 else "balanced" if mean_value < 0.22 else "bright"
    return f"Centroid stays {brightness} overall, peaks at {peak_value:.3f}, and trends {trend}."


def describe_flux(mean_value: float, peak_value: float, onset_count: int) -> str:
    texture = "spiky" if peak_value >= mean_value * 3 and peak_value > 0 else "steady"
    return f"Onset flux is {texture} with mean {mean_value:.3f}, peak {peak_value:.3f}, and {onset_count} detected onset anchors."


def _mean(values: list[float]) -> float:
    return float(fmean(values)) if values else 0.0


def _std(values: list[float]) -> float:
    return float(pstdev(values)) if len(values) > 1 else 0.0