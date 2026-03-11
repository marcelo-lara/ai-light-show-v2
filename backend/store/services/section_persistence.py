import contextlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple


def normalize_sections_input(sections: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for row in sections or []:
        name = str((row or {}).get("name") or "").strip()
        if not name:
            return False, {"ok": False, "reason": "invalid_name"}

        try:
            start = float((row or {}).get("start"))
            end = float((row or {}).get("end"))
        except (TypeError, ValueError):
            return False, {"ok": False, "reason": "invalid_time"}

        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            return False, {"ok": False, "reason": "invalid_range"}

        normalized.append({"name": name, "start": start, "end": end})

    normalized.sort(key=lambda item: item["start"])
    for index in range(1, len(normalized)):
        if normalized[index]["start"] < normalized[index - 1]["end"]:
            return False, {"ok": False, "reason": "overlap"}

    unique_name_counts: Dict[str, int] = {}
    parts: Dict[str, List[float]] = {}
    for row in normalized:
        base_name = row["name"]
        count = unique_name_counts.get(base_name, 0) + 1
        unique_name_counts[base_name] = count
        key = base_name if count == 1 else f"{base_name} ({count})"
        parts[key] = [float(row["start"]), float(row["end"])]

    return True, {"ok": True, "parts": parts}


def persist_parts_to_meta(
    *,
    song_filename: str,
    parts: Dict[str, List[float]],
    meta_candidates: List[Path],
    meta_path: Path,
) -> None:
    target_file = None
    for candidate in meta_candidates:
        if candidate.exists():
            target_file = candidate
            break
    if not target_file:
        target_file = meta_path / song_filename / f"{song_filename}.json"

    target_file.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {}
    if target_file.exists():
        with contextlib.suppress(OSError, ValueError, TypeError):
            with open(target_file, "r") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                payload = loaded

    if "filename" not in payload:
        payload["filename"] = song_filename
    payload["parts"] = parts

    with open(target_file, "w") as handle:
        json.dump(payload, handle, indent=2)
