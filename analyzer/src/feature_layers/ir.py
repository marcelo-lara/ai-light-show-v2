from __future__ import annotations

from pathlib import Path
from typing import Any

from ..storage.song_meta import canonical_beats_path, load_json_file, load_sections


def build_music_feature_layers(song_path: Path, meta_path: Path, harmonic: dict[str, Any], symbolic: dict[str, Any], energy: dict[str, Any]) -> dict[str, Any]:
    meta_dir = meta_path / song_path.stem
    info = load_json_file(meta_dir / "info.json") if (meta_dir / "info.json").exists() else {}
    beats_file = canonical_beats_path(song_path, meta_path)
    beats_rows = load_json_file(beats_file) if beats_file.exists() else []
    beats = [row for row in beats_rows if isinstance(row, dict)]
    sections = load_sections(meta_dir)
    return {
        "schema_version": "1.0",
        "song_id": song_path.stem,
        "source_song_path": str(song_path),
        "generated_from": {
            "info_file": str(meta_dir / "info.json"),
            "beats_file": str(beats_file),
            "harmonic_layer_file": str(meta_dir / "layer_a_harmonic.json"),
            "symbolic_layer_file": str(meta_dir / "layer_b_symbolic.json"),
            "energy_layer_file": str(meta_dir / "layer_c_energy.json"),
        },
        "metadata": {
            "title": song_path.stem,
            "artist": _artist(song_path.stem),
            "duration_s": float(info.get("duration", 0.0) or 0.0),
            "bpm": float(info.get("bpm", 0.0) or 0.0),
            "time_signature": "4/4",
            "key": str((harmonic.get("global_key") or {}).get("label") or ""),
            "key_confidence": float((harmonic.get("global_key") or {}).get("confidence") or 0.0),
        },
        "timeline": {
            "beats": beats,
            "bars": _bars(beats),
            "sections": sections,
            "accent_windows": energy.get("accent_candidates") or [],
        },
        "layers": {
            "harmonic": harmonic,
            "symbolic": symbolic,
            "energy": energy,
        },
        "energy_profile": _energy_profile(energy),
        "structure_summary": _structure_summary(sections, energy),
        "section_cards": _section_cards(sections, harmonic, symbolic, energy),
        "mapping_rules": _mapping_rules(energy),
        "generation_notes": [*harmonic.get("validation_notes", []), *symbolic.get("validation_notes", []), *energy.get("validation_notes", [])],
    }


def _artist(song_id: str) -> str:
    return song_id.split(" - ", 1)[0] if " - " in song_id else ""


def _bars(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bars: dict[int, dict[str, Any]] = {}
    for beat in beats:
        bar = int(beat.get("bar", 0) or 0)
        time_value = float(beat.get("time", 0.0) or 0.0)
        payload = bars.setdefault(bar, {"bar": bar, "start_s": time_value, "end_s": time_value})
        payload["start_s"] = min(payload["start_s"], time_value)
        payload["end_s"] = max(payload["end_s"], time_value)
    return [bars[key] for key in sorted(bars)]


def _structure_summary(sections: list[dict[str, Any]], energy: dict[str, Any]) -> str:
    if not sections:
        return "No section data available."
    profile = _energy_profile(energy)
    trend = profile.get("energy_trend") or "unknown"
    brightness = profile.get("brightness_trend") or "unknown"
    onsets = int(profile.get("onset_count") or 0)
    return f"{len(sections)} sections with an overall {trend} energy trend, {brightness} brightness arc, and {onsets} detected onset anchors."


def _section_cards(sections: list[dict[str, Any]], harmonic: dict[str, Any], symbolic: dict[str, Any], energy: dict[str, Any]) -> list[dict[str, Any]]:
    harmonic_sections = {item.get("section_name"): item for item in harmonic.get("section_harmony") or [] if isinstance(item, dict)}
    symbolic_sections = {item.get("section_name"): item for item in symbolic.get("section_symbolic") or [] if isinstance(item, dict)}
    energy_sections = {item.get("section_name"): item for item in energy.get("section_energy") or [] if isinstance(item, dict)}
    cards: list[dict[str, Any]] = []
    for section in sections:
        harmonic_row = harmonic_sections.get(section["name"], {})
        symbolic_row = symbolic_sections.get(section["name"], {})
        energy_row = energy_sections.get(section["name"], {})
        cards.append(
            {
                "section_name": section["name"],
                "start_s": section["start_s"],
                "end_s": section["end_s"],
                "music_description": energy_row.get("summary") or symbolic_row.get("summary") or harmonic_row.get("summary") or "No summary available.",
                "harmonic_notes": harmonic_row,
                "symbolic_notes": symbolic_row,
                "energy_notes": energy_row,
                "energy_profile": _section_energy_profile(energy_row),
                "energy_description": _section_energy_description(energy_row),
                "visual_implications": _visual_implications(energy_row),
            }
        )
    return cards


def _mapping_rules(energy: dict[str, Any]) -> list[str]:
    profile = _energy_profile(energy)
    level = profile.get("energy_trend") or "unknown"
    brightness = profile.get("brightness_trend") or "unknown"
    return [
        "Bass -> dimmer pulses",
        "Chord change -> color shift",
        f"Global energy trend -> {level} movement scaling",
        f"Brightness trend -> {brightness} color temperature shaping",
        f"Onset anchors -> {int(profile.get('onset_count') or 0)} timing accents",
    ]


def _visual_implications(energy_row: dict[str, Any]) -> list[str]:
    level = str(energy_row.get("level") or "unknown")
    if level == "high":
        return ["Open the rig", "Increase brightness", "Use wider sweeps"]
    if level == "low":
        return ["Narrow the rig", "Reduce brightness", "Favor holds over chases"]
    return ["Maintain readable groove", "Use phrase-led motion"]


def _energy_profile(energy: dict[str, Any]) -> dict[str, Any]:
    global_energy = (energy.get("global_energy") or {}) if isinstance(energy.get("global_energy"), dict) else {}
    loudness = (energy.get("loudness_profile") or {}) if isinstance(energy.get("loudness_profile"), dict) else {}
    onsets = (energy.get("onset_profile") or {}) if isinstance(energy.get("onset_profile"), dict) else {}
    spectral = (energy.get("spectral_profile") or {}) if isinstance(energy.get("spectral_profile"), dict) else {}
    return {
        "energy_trend": str(global_energy.get("energy_trend") or "unknown"),
        "dynamic_range": float(global_energy.get("dynamic_range", 0.0) or 0.0),
        "transient_density": float(global_energy.get("transient_density", 0.0) or 0.0),
        "loudness_mean": float(loudness.get("mean", 0.0) or 0.0),
        "loudness_peak": float(loudness.get("peak", 0.0) or 0.0),
        "loudness_percentile_90": float(loudness.get("percentile_90", 0.0) or 0.0),
        "onset_count": int(onsets.get("onset_count", 0) or 0),
        "onset_density_per_minute": float(onsets.get("onset_density_per_minute", 0.0) or 0.0),
        "flux_mean": float(onsets.get("flux_mean", 0.0) or 0.0),
        "flux_peak": float(onsets.get("flux_peak", 0.0) or 0.0),
        "brightness_trend": str(spectral.get("brightness_trend") or "unknown"),
        "centroid_mean": float(spectral.get("centroid_mean", 0.0) or 0.0),
        "centroid_peak": float(spectral.get("centroid_peak", 0.0) or 0.0),
        "centroid_summary": str(spectral.get("centroid_summary") or ""),
        "flux_summary": str(spectral.get("flux_summary") or ""),
    }


def _section_energy_description(energy_row: dict[str, Any]) -> str:
    level = str(energy_row.get("level") or "unknown")
    trend = str(energy_row.get("trend") or "unknown")
    loudness_peak = float(energy_row.get("loudness_peak", 0.0) or 0.0)
    centroid_mean = float(energy_row.get("centroid_mean", 0.0) or 0.0)
    return f"{level.capitalize()} energy with a {trend} contour, loudness peak {loudness_peak:.3f}, centroid mean {centroid_mean:.3f}."


def _section_energy_profile(energy_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "level": str(energy_row.get("level") or "unknown"),
        "trend": str(energy_row.get("trend") or "unknown"),
        "transient_density": float(energy_row.get("transient_density", 0.0) or 0.0),
        "loudness_mean": float(energy_row.get("loudness_mean", 0.0) or 0.0),
        "loudness_peak": float(energy_row.get("loudness_peak", 0.0) or 0.0),
        "centroid_mean": float(energy_row.get("centroid_mean", 0.0) or 0.0),
        "centroid_peak": float(energy_row.get("centroid_peak", 0.0) or 0.0),
        "flux_mean": float(energy_row.get("flux_mean", 0.0) or 0.0),
    }