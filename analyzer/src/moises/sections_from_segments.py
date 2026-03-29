from __future__ import annotations

import json
import math
from pathlib import Path


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, list) else []


def _float_or_none(value) -> float | None:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _normalize_segment_row(row: dict) -> dict | None:
    start_value = _float_or_none(row.get("start"))
    end_value = _float_or_none(row.get("end"))
    label_value = str(row.get("label") or "").strip()
    if start_value is None or end_value is None or not label_value:
        return None
    return {"start": start_value, "end": end_value, "label": label_value, "description": "", "hints": []}


def validate_sections_rows(rows: list[dict]) -> tuple[bool, str]:
    normalized: list[dict[str, float]] = []
    for row in rows:
        label = str((row or {}).get("label") or "").strip()
        start = _float_or_none((row or {}).get("start"))
        end = _float_or_none((row or {}).get("end"))
        if not label:
            return False, "invalid_name"
        if start is None or end is None:
            return False, "invalid_time"
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            return False, "invalid_range"
        normalized.append({"start": start, "end": end})

    normalized.sort(key=lambda item: item["start"])
    for index in range(1, len(normalized)):
        if normalized[index]["start"] < normalized[index - 1]["end"]:
            return False, "overlap"
    return True, "ok"


def generate_sections_from_segments(song_meta_dir: Path) -> Path | None:
    sections_path = song_meta_dir / "sections.json"
    if sections_path.exists():
        return sections_path

    segment_rows = _load_rows(song_meta_dir / "moises" / "segments.json")
    if not segment_rows:
        return None

    sections_rows: list[dict] = []
    for segment_row in segment_rows:
        normalized = _normalize_segment_row(segment_row)
        if normalized is None:
            print(f"ERROR: invalid Moises segment row found for {song_meta_dir.name}")
            return None
        sections_rows.append(normalized)

    is_valid, reason = validate_sections_rows(sections_rows)
    if not is_valid:
        print(f"ERROR: Moises segments failed section validation for {song_meta_dir.name}: {reason}")
        return None

    with open(sections_path, "w", encoding="utf-8") as handle:
        json.dump(sections_rows, handle, indent=4)
    print(f"Successfully generated sections from Moises segments at {sections_path}")
    return sections_path