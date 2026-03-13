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
            
            # Simple conversion rule - standard absolute URL pattern mapping
            svg_url = value.get("svg")
            if not svg_url:
                continue
            
            # Handle standard app mount mapping /app/meta/x -> /meta/x
            if str(svg_url).startswith("/app/meta/"):
                mapped_path_parts = Path(svg_url[len("/app/meta/"):]).parts
                svg_url = f"/meta/{'/'.join(quote(part) for part in mapped_path_parts)}"

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

    meta = song.meta
    beats = song.beats
    sections = song.sections
    
    sections_list = []
    if sections and sections.sections:
        for s in sections.sections:
            start_raw = s.get("start_s")
            if start_raw is None:
                start_raw = s.get("start")

            end_raw = s.get("end_s")
            if end_raw is None:
                end_raw = s.get("end")

            name_raw = s.get("name")
            if not name_raw:
                name_raw = s.get("label")

            sections_list.append({
                "name": str(name_raw or ""),
                "start_s": float(start_raw or 0.0),
                "end_s": float(end_raw or 0.0),
            })
        
    sections_list.sort(key=lambda item: item.get("start_s", 0.0))

    return {
        "filename": song.song_id,
        "audio_url": song.audio_url,
        "length_s": meta.duration if meta else None,
        "bpm": meta.bpm if meta else None,
        "sections": sections_list,
        "beats": [beat.model_dump() for beat in beats.beats] if beats else [],
        "analysis": build_song_analysis_payload(manager, song.song_id),
    }
