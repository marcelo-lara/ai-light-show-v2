from __future__ import annotations

from typing import Any, Dict, List, Optional


def pick_numeric_list(*candidates: Any) -> List[float]:
    for candidate in candidates:
        if not isinstance(candidate, list):
            continue
        picked: List[float] = []
        for value in candidate:
            try:
                picked.append(float(value))
            except Exception:
                continue
        if picked:
            return picked
    return []


def build_song_payload(manager) -> Optional[Dict[str, Any]]:
    song = manager.state_manager.current_song
    if not song:
        return None

    metadata = getattr(song, "metadata", None)
    hints = getattr(metadata, "hints", {}) or {}
    drums = getattr(metadata, "drums", {}) or {}
    parts = getattr(metadata, "parts", {}) or {}

    sections: List[Dict[str, Any]] = []
    for name, rng in parts.items():
        if not isinstance(rng, list) or len(rng) < 2:
            continue
        try:
            start = float(rng[0])
            end = float(rng[1])
        except Exception:
            continue
        sections.append({"name": str(name), "start_s": start, "end_s": end})
    sections.sort(key=lambda item: float(item.get("start_s", 0.0)))

    return {
        "filename": str(getattr(song, "filename", "") or ""),
        "audio_url": getattr(song, "audioUrl", None),
        "length_s": getattr(metadata, "length", None),
        "bpm": getattr(metadata, "bpm", None),
        "sections": sections,
        "beats": pick_numeric_list(hints.get("beats"), drums.get("beats")),
        "downbeats": pick_numeric_list(hints.get("downbeats"), drums.get("downbeats")),
    }
