from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote


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


def to_meta_url(path: Path, meta_root: Path) -> Optional[str]:
    with_meta = None
    with_suppress = False
    try:
        with_meta = path.resolve().relative_to(meta_root.resolve())
    except Exception:
        with_suppress = True

    if with_suppress or with_meta is None:
        return None

    encoded = "/".join(quote(part) for part in with_meta.parts)
    return f"/meta/{encoded}"


def resolve_artifact_meta_url(manager, raw_path: Any, meta_root: Path, meta_file: Path) -> Optional[str]:
    text = str(raw_path or "").strip()
    if not text:
        return None

    if text.startswith("http://") or text.startswith("https://"):
        return text

    if text.startswith("/app/meta/"):
        encoded = "/".join(quote(part) for part in Path(text[len("/app/meta/"):]).parts)
        return f"/meta/{encoded}"

    if text.startswith("/meta/"):
        return text

    resolved = manager.state_manager._resolve_analyzer_artifact_path(text, meta_file)
    if resolved:
        url = to_meta_url(resolved, meta_root)
        if url:
            return url

    fallback = meta_file.parent / text
    if fallback.exists():
        return to_meta_url(fallback, meta_root)

    return None


def parse_chords(chords_path: Path) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(chords_path.read_text())
    except Exception:
        return []

    if not isinstance(payload, list):
        return []

    picked: List[Dict[str, Any]] = []
    previous_label = ""
    for row in payload:
        if not isinstance(row, dict):
            continue

        label = str(
            row.get("chord_simple_pop")
            or row.get("chord_basic_pop")
            or row.get("prev_chord")
            or ""
        ).strip()
        if not label or label.upper() == "N" or label == previous_label:
            continue

        try:
            time_s = float(row.get("curr_beat_time", 0.0))
        except Exception:
            continue

        entry: Dict[str, Any] = {"time_s": time_s, "label": label}
        if isinstance(row.get("bar_num"), int):
            entry["bar"] = int(row["bar_num"])
        if isinstance(row.get("beat_num"), int):
            entry["beat"] = int(row["beat_num"])
        picked.append(entry)
        previous_label = label

    return picked[:512]


def build_song_analysis_payload(manager, song_filename: str) -> Optional[Dict[str, Any]]:
    meta_root = Path(getattr(manager.state_manager, "meta_path", "") or "")
    if not meta_root:
        return None

    info_file = meta_root / song_filename / "info.json"
    if not info_file.exists():
        return None

    try:
        info_data = json.loads(info_file.read_text())
    except Exception:
        return None

    if not isinstance(info_data, dict):
        return None

    artifacts = info_data.get("artifacts") or {}
    essentia = artifacts.get("essentia") if isinstance(artifacts, dict) else None

    plots: List[Dict[str, Any]] = []
    if isinstance(essentia, dict):
        for key, value in essentia.items():
            if not isinstance(value, dict):
                continue
            svg_url = resolve_artifact_meta_url(manager, value.get("svg"), meta_root, info_file)
            if not svg_url:
                continue
            plots.append({"id": str(key), "title": str(key).replace("_", " ").title(), "svg_url": svg_url})

    chords_path = meta_root / song_filename / "moises" / "chords.json"
    chords = parse_chords(chords_path) if chords_path.exists() else []

    if not plots and not chords:
        return None

    return {"plots": plots, "chords": chords}


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
        "analysis": build_song_analysis_payload(manager, str(getattr(song, "filename", "") or "")),
    }
