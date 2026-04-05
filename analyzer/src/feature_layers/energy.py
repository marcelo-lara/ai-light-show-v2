from __future__ import annotations

from pathlib import Path
from typing import Any

from .energy_support import load_rhythm, load_series, loudness_summary, onset_summary, section_series_stats, spectral_summary
from ..storage.song_meta import load_json_file, load_sections


def build_energy_layer(song_path: Path, meta_path: Path) -> dict[str, Any]:
    meta_dir = meta_path / song_path.stem
    features = load_json_file(meta_dir / "features.json") if (meta_dir / "features.json").exists() else {}
    hints = load_json_file(meta_dir / "hints.json") if (meta_dir / "hints.json").exists() else []
    sections = load_sections(meta_dir)
    global_energy = (((features.get("global") or {}).get("energy") or {}) if isinstance(features, dict) else {})
    feature_sections = (features.get("sections") or []) if isinstance(features, dict) else []
    accent_candidates = _accent_candidates(hints)
    loudness_series = load_series(meta_dir, "loudness_envelope.json", "loudness")
    centroid_series = load_series(meta_dir, "spectral_centroid.json", "centroid")
    rhythm_payload = load_rhythm(meta_dir)
    duration_s = float((features.get("global") or {}).get("duration_s", 0.0) or 0.0) if isinstance(features, dict) else 0.0
    loudness_profile = loudness_summary(loudness_series, accent_candidates)
    onset_profile = onset_summary(rhythm_payload, accent_candidates, duration_s)
    spectral_profile = spectral_summary(centroid_series, onset_profile, sections)
    section_energy = [_section_energy(section, feature_sections, loudness_series, centroid_series, onset_profile) for section in sections]
    return {
        "schema_version": "1.0",
        "song_id": song_path.stem,
        "generated_from": {
            "features_file": str(meta_dir / "features.json"),
            "hints_file": str(meta_dir / "hints.json"),
            "sections_file": str(meta_dir / "sections.json"),
            "loudness_file": str(loudness_series.get("path")),
            "spectral_centroid_file": str(centroid_series.get("path")),
            "rhythm_file": str(rhythm_payload.get("path") or (meta_dir / "essentia" / "rhythm.json")),
        },
        "global_energy": {
            "mean": float(global_energy.get("mean", 0.0) or 0.0),
            "peak": float(global_energy.get("peak", 0.0) or 0.0),
            "dynamic_range": float(global_energy.get("dynamic_range", 0.0) or 0.0),
            "transient_density": float(global_energy.get("volatility", 0.0) or 0.0),
            "energy_trend": _global_trend(section_energy),
        },
        "loudness_profile": loudness_profile,
        "onset_profile": onset_profile,
        "spectral_profile": spectral_profile,
        "section_energy": section_energy,
        "notable_peaks": [item for item in section_energy if item["level"] == "high"],
        "notable_dips": [item for item in section_energy if item["level"] == "low"],
        "accent_candidates": accent_candidates,
        "validation_notes": _validation_notes(section_energy, loudness_series, centroid_series, rhythm_payload),
    }


def _section_energy(section: dict[str, Any], feature_sections: list[dict[str, Any]], loudness_series: dict[str, Any], centroid_series: dict[str, Any], onset_profile: dict[str, Any]) -> dict[str, Any]:
    match = next((row for row in feature_sections if isinstance(row, dict) and row.get("name") == section["name"] and float(row.get("start_s", -1.0)) == section["start_s"]), {})
    energy = (match.get("energy") or {}) if isinstance(match, dict) else {}
    parts = [item.get("part") for item in (match.get("dominant_parts") or []) if isinstance(item, dict) and item.get("part")]
    level = str(energy.get("level") or _peak_level(float(energy.get("peak", 0.0) or 0.0)))
    loudness = section_series_stats(loudness_series, section["start_s"], section["end_s"])
    centroid = section_series_stats(centroid_series, section["start_s"], section["end_s"])
    return {
        "section_id": f"{section['name'].lower().replace(' ', '-')}-{section['start_s']:.2f}",
        "section_name": section["name"],
        "start_s": section["start_s"],
        "end_s": section["end_s"],
        "level": level,
        "trend": str(energy.get("trend") or "unknown"),
        "mean": float(energy.get("mean", 0.0) or 0.0),
        "peak": float(energy.get("peak", 0.0) or 0.0),
        "transient_density": float(energy.get("volatility", 0.0) or 0.0),
        "loudness_mean": loudness["mean"],
        "loudness_peak": loudness["peak"],
        "centroid_mean": centroid["mean"],
        "centroid_peak": centroid["peak"],
        "flux_mean": float(onset_profile.get("flux_mean", 0.0) or 0.0),
        "dominant_parts": parts[:4],
        "summary": str(match.get("summary") or f"{section['name']} energy is {level}."),
    }


def _accent_candidates(hints: object) -> list[dict[str, Any]]:
    rows = hints if isinstance(hints, list) else []
    return [
        {
            "time": float(item.get("time_s", 0.0) or 0.0),
            "kind": str(item.get("kind") or "unknown"),
            "intensity": float(item.get("strength", 0.0) or 0.0),
            "related_parts": item.get("parts") or [],
            "section_name": str(section.get("name") or ""),
        }
        for section in rows if isinstance(section, dict)
        for item in (section.get("hints") or []) if isinstance(item, dict)
    ]


def _global_trend(section_energy: list[dict[str, Any]]) -> str:
    labels = [item["level"] for item in section_energy]
    if not labels:
        return "unknown"
    if labels[:1] == ["low"] and labels[-1:] == ["high"]:
        return "low-to-high"
    if len(set(labels)) == 1:
        return "plateau"
    return "wave"


def _peak_level(value: float) -> str:
    if value >= 2.0:
        return "high"
    if value >= 0.75:
        return "mid"
    return "low"


def _validation_notes(section_energy: list[dict[str, Any]], loudness_series: dict[str, Any], centroid_series: dict[str, Any], rhythm_payload: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    if not section_energy:
        notes.append("No section energy data available.")
    if not loudness_series.get("values"):
        notes.append("No Essentia loudness envelope available; loudness summaries fall back to feature metadata.")
    if not centroid_series.get("values"):
        notes.append("No Essentia spectral centroid available; brightness summaries fall back to section energy trends.")
    onsets = rhythm_payload.get("onsets") if isinstance(rhythm_payload.get("onsets"), dict) else {}
    if not onsets.get("rate"):
        notes.append("No Essentia onset flux available; onset summaries fall back to analyzer hints.")
    return notes