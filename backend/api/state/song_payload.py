from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from models.song.artifacts import build_essentia_plot_descriptors
from models.song.io import resolve_beats_file

logger = logging.getLogger(__name__)

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
    """Parse chords from the analyzer canonical beats format"""
    try:
        payload = json.loads(chords_path.read_text())
    except Exception:
        return []

    if not isinstance(payload, list):
        return []

    raw_sample = [
        {
            "time": row.get("time"),
            "beat": row.get("beat"),
            "bar": row.get("bar"),
            "chord": row.get("chord"),
        }
        for row in payload[:8]
        if isinstance(row, dict)
    ]
    logger.debug("[SONG_PAYLOAD] beats sample %s -> %s", chords_path, raw_sample)

    picked: List[Dict[str, Any]] = []
    previous_label = ""
    skipped_no_label = 0
    skipped_duplicate = 0
    for row in payload:
        if not isinstance(row, dict):
            continue

        label = str(row.get("chord") or "").strip()
        if not label:
            skipped_no_label += 1
            continue
        if label == previous_label:
            skipped_duplicate += 1
            continue

        try:
            time_s = float(row.get("time", 0.0))
        except Exception:
            continue

        entry: Dict[str, Any] = {"time_s": time_s, "label": label}
        if isinstance(row.get("bar"), int):
            entry["bar"] = int(row["bar"])
        if isinstance(row.get("beat"), int):
            entry["beat"] = int(row["beat"])
        picked.append(entry)
        previous_label = label

    logger.debug(
        "[SONG_PAYLOAD] parsed chords %s -> kept=%s skipped_empty=%s skipped_duplicate=%s first_kept=%s",
        chords_path,
        len(picked),
        skipped_no_label,
        skipped_duplicate,
        picked[:8],
    )

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

    plots: List[Dict[str, Any]] = []
    for plot in build_essentia_plot_descriptors(artifacts if isinstance(artifacts, dict) else None):
        svg_url = plot.get("svg")
        if not svg_url:
            continue
        if str(svg_url).startswith("/app/meta/"):
            mapped_path_parts = Path(str(svg_url)[len("/app/meta/"):]).parts
            svg_url = f"/meta/{'/'.join(quote(part) for part in mapped_path_parts)}"
        plots.append({"id": str(plot["id"]), "title": str(plot["title"]), "svg_url": svg_url})

    chords_path = Path(resolve_beats_file(meta_root / song_filename, info_data))
    chords = parse_chords(chords_path) if chords_path.exists() else []
    logger.debug(
        "[SONG_PAYLOAD] analysis payload for %s -> chords=%s first=%s",
        song_filename,
        len(chords),
        chords[:8],
    )

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
