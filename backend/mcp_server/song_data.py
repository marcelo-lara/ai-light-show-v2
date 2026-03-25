from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote


def _normalize_sections(raw_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for section in raw_sections or []:
        start_value = section.get("start_s", section.get("start", 0.0))
        end_value = section.get("end_s", section.get("end", 0.0))
        name_value = section.get("name") or section.get("label") or ""
        normalized.append(
            {
                "name": str(name_value),
                "start_s": float(start_value or 0.0),
                "end_s": float(end_value or 0.0),
            }
        )
    normalized.sort(key=lambda item: item["start_s"])
    return normalized


def _parse_chords(beats_path: Path) -> List[Dict[str, Any]]:
    if not beats_path.exists():
        return []
    try:
        payload = json.loads(beats_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []

    chords: List[Dict[str, Any]] = []
    previous_label = ""
    for row in payload:
        if not isinstance(row, dict):
            continue
        label = str(row.get("chord") or "").strip()
        if not label or label == previous_label:
            continue
        entry: Dict[str, Any] = {"time_s": float(row.get("time", 0.0)), "label": label}
        if isinstance(row.get("bar"), int):
            entry["bar"] = row["bar"]
        if isinstance(row.get("beat"), int):
            entry["beat"] = row["beat"]
        chords.append(entry)
        previous_label = label
    return chords[:512]


def _build_plots(song, meta_root: Path) -> List[Dict[str, Any]]:
    artifacts = getattr(song.meta, "artifacts", {}) or {}
    essentia = artifacts.get("essentia") if isinstance(artifacts, dict) else None
    plots: List[Dict[str, Any]] = []
    if not isinstance(essentia, dict):
        return plots
    for key, value in essentia.items():
        if not isinstance(value, dict) or not value.get("svg"):
            continue
        svg_url = str(value["svg"])
        if svg_url.startswith("/app/meta/"):
            parts = Path(svg_url[len("/app/meta/"):]).parts
            svg_url = f"/meta/{'/'.join(quote(part) for part in parts)}"
        plots.append({"id": str(key), "title": str(key).replace("_", " ").title(), "svg_url": svg_url})
    return plots


def build_song_details(song, meta_root: Path) -> Dict[str, Any]:
    beats = [beat.model_dump() for beat in song.beats.beats]
    sections = _normalize_sections(song.sections.sections)
    chords = _parse_chords(meta_root / song.song_id / "beats.json")
    analysis: Optional[Dict[str, Any]] = None
    plots = _build_plots(song, meta_root)
    if plots or chords:
        analysis = {"plots": plots, "chords": chords}
    return {
        "filename": song.song_id,
        "audio_url": song.audio_url,
        "length_s": song.meta.duration,
        "bpm": song.meta.bpm,
        "sections": sections,
        "beats": beats,
        "analysis": analysis,
    }