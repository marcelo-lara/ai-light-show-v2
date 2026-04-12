from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from models.song.analysis_files import resolve_meta_path
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


def local_data_root(meta_root: Path) -> Path:
    if meta_root.name in {"meta", "output"}:
        return meta_root.parent
    return meta_root

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


def resolve_output_file(song_dir: Path, info_data: Dict[str, Any], song_filename: str, output_key: str, default_name: str) -> Path:
    outputs = info_data.get("outputs") if isinstance(info_data, dict) else None
    candidate = outputs.get(output_key) if isinstance(outputs, dict) else None
    raw_path = candidate if isinstance(candidate, str) else ""
    resolved = resolve_meta_path(song_dir.parent, raw_path, song_filename, default_name)
    fallback = song_dir / default_name
    if raw_path and not resolved.exists() and fallback.exists():
        return fallback
    return resolved


def resolve_artifact_file(
    song_dir: Path,
    info_data: Dict[str, Any],
    song_filename: str,
    artifact_key: str,
    default_relative_path: str,
) -> Path:
    artifacts = info_data.get("artifacts") if isinstance(info_data, dict) else None
    candidate = artifacts.get(artifact_key) if isinstance(artifacts, dict) else None
    raw_path = candidate if isinstance(candidate, str) else ""
    fallback = local_data_root(song_dir.parent) / "artifacts" / song_filename / default_relative_path
    if raw_path:
        resolved = resolve_meta_path(song_dir.parent, raw_path, song_filename, default_relative_path)
        if not resolved.exists() and fallback.exists():
            return fallback
        return resolved
    return fallback


def parse_song_events(events_path: Path) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(events_path.read_text())
    except Exception:
        return []

    rows = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []

    picked: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        event_id = str(row.get("id") or "").strip()
        event_type = str(row.get("type") or "").strip()
        if not event_id or not event_type:
            continue

        try:
            start_time = float(row.get("start_time"))
            end_time = float(row.get("end_time"))
        except Exception:
            continue
        if not (start_time >= 0.0 and end_time > start_time):
            continue

        try:
            confidence = float(row.get("confidence", 0.0))
        except Exception:
            confidence = 0.0
        try:
            intensity = float(row.get("intensity", 0.0))
        except Exception:
            intensity = 0.0

        section_name_raw = row.get("section_name")
        picked.append({
            "id": event_id,
            "type": event_type,
            "start_time": start_time,
            "end_time": end_time,
            "confidence": confidence,
            "intensity": intensity,
            "section_id": str(row.get("section_id") or "").strip(),
            "section_name": None if section_name_raw is None else str(section_name_raw).strip(),
            "provenance": str(row.get("provenance") or "").strip(),
            "summary": str(row.get("summary") or "").strip(),
            "created_by": str(row.get("created_by") or "").strip(),
            "evidence_summary": str(row.get("evidence_summary") or "").strip(),
            "lighting_hint": str(row.get("lighting_hint") or "").strip(),
        })

    picked.sort(key=lambda item: (item["start_time"], item["end_time"], item["id"]))
    return picked[:1024]


def parse_chord_patterns(patterns_path: Path) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(patterns_path.read_text())
    except Exception:
        return []

    rows = payload.get("patterns") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []

    picked: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        pattern_id = str(row.get("id") or "").strip()
        label = str(row.get("label") or "").strip()
        sequence = str(row.get("sequence") or "").strip()
        if not pattern_id or not label or not sequence:
            continue

        try:
            bar_count = int(row.get("bar_count"))
        except Exception:
            continue
        if bar_count <= 0:
            continue

        occurrences_raw = row.get("occurrences")
        if not isinstance(occurrences_raw, list):
            occurrences_raw = []

        occurrences: List[Dict[str, Any]] = []
        for occurrence in occurrences_raw:
            if not isinstance(occurrence, dict):
                continue
            try:
                start_bar = int(occurrence.get("start_bar"))
                end_bar = int(occurrence.get("end_bar"))
                start_s = float(occurrence.get("start_s"))
                end_s = float(occurrence.get("end_s"))
            except Exception:
                continue
            if start_bar < 0 or end_bar <= start_bar or end_s <= start_s:
                continue
            try:
                mismatch_count = int(occurrence.get("mismatch_count", 0))
            except Exception:
                mismatch_count = 0
            occurrences.append({
                "start_bar": start_bar,
                "end_bar": end_bar,
                "start_s": start_s,
                "end_s": end_s,
                "mismatch_count": mismatch_count,
                "sequence": str(occurrence.get("sequence") or "").strip(),
            })

        if not occurrences:
            continue

        occurrences.sort(key=lambda item: (item["start_s"], item["end_s"], item["start_bar"]))
        picked.append({
            "id": pattern_id,
            "label": label,
            "bar_count": bar_count,
            "sequence": sequence,
            "occurrence_count": len(occurrences),
            "occurrences": occurrences,
        })

    picked.sort(key=lambda item: (-item["occurrence_count"], item["label"], item["id"]))
    return picked[:128]

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
    song_dir = meta_root / song_filename
    events_path = resolve_output_file(song_dir, info_data, song_filename, "song_event_timeline", "song_event_timeline.json")
    events = parse_song_events(events_path) if events_path.exists() else []
    patterns_path = resolve_artifact_file(song_dir, info_data, song_filename, "pattern_mining", "pattern_mining/chord_patterns.json")
    patterns = parse_chord_patterns(patterns_path) if patterns_path.exists() else []
    logger.debug(
        "[SONG_PAYLOAD] analysis payload for %s -> chords=%s events=%s patterns=%s first_pattern=%s",
        song_filename,
        len(chords),
        len(events),
        len(patterns),
        patterns[:2],
    )

    if not plots and not chords and not events and not patterns:
        return None

    return {"plots": plots, "chords": chords, "events": events, "patterns": patterns}

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
