from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .beats import Beat


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def resolve_meta_path(meta_root: Path, raw_path: str, song_id: str, fallback_name: str) -> Path:
    if raw_path.startswith("/app/meta/"):
        return meta_root / raw_path[len("/app/meta/"):]
    if raw_path:
        return Path(raw_path)
    return meta_root / song_id / fallback_name


def normalize_sections(raw_sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section in raw_sections or []:
        start_s = float(section.get("start_s", section.get("start", 0.0)) or 0.0)
        end_s = float(section.get("end_s", section.get("end", start_s)) or start_s)
        name = str(section.get("name") or section.get("label") or "")
        sections.append({"name": name, "start_s": start_s, "end_s": end_s})
    sections.sort(key=lambda item: item["start_s"])
    return sections


def attach_section_positions(sections: list[dict[str, Any]], beats: list[Beat]) -> list[dict[str, Any]]:
    if not beats:
        return sections
    beat_rows = [beat.model_dump() for beat in beats]
    positioned: list[dict[str, Any]] = []
    for section in sections:
        entry = dict(section)
        for prefix, time_key in (("start", "start_s"), ("end", "end_s")):
            match = find_last_beat_at_or_before(beat_rows, float(section.get(time_key, 0.0)))
            if match is not None:
                entry[f"{prefix}_bar"] = int(match.get("bar", 0))
                entry[f"{prefix}_beat"] = int(match.get("beat", 0))
        positioned.append(entry)
    return positioned


def find_last_beat_at_or_before(beats: list[dict[str, Any]], time_s: float) -> dict[str, Any] | None:
    match: dict[str, Any] | None = None
    for beat in beats:
        if float(beat.get("time", 0.0)) <= time_s:
            match = beat
            continue
        break
    if match is not None:
        return match
    return beats[0] if beats else None