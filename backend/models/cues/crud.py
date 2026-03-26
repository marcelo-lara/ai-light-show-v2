from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import CueEntry, CueSheet


DUPLICATE_WINDOW_SECONDS = 0.1


def _round_floats_for_save(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, dict):
        return {k: _round_floats_for_save(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round_floats_for_save(item) for item in value]
    return value


def cue_file_path(cues_path: Path, song_filename: str) -> Path:
    return cues_path / f"{song_filename}.json"


def load_cue_sheet(cues_path: Path, song_filename: str) -> CueSheet:
    cue_file = cue_file_path(cues_path, song_filename)
    if not cue_file.exists():
        return CueSheet(song_filename=song_filename)
    with open(cue_file, "r") as f:
        raw = json.load(f)
    entries = [CueEntry(**item) for item in raw]
    return CueSheet(song_filename=song_filename, entries=entries)


def save_cue_sheet(cues_path: Path, cue_sheet: CueSheet) -> None:
    cues_path.mkdir(parents=True, exist_ok=True)
    cue_file = cue_file_path(cues_path, cue_sheet.song_filename)
    entries = [_round_floats_for_save(entry.model_dump(exclude_none=True)) for entry in cue_sheet.entries]
    with open(cue_file, "w") as f:
        json.dump(entries, f, indent=2)


def clear_cue_sheet(
    cues_path: Path,
    song_filename: str,
    from_time: float = 0.0,
    to_time: Optional[float] = None,
) -> None:
    cue_file = cue_file_path(cues_path, song_filename)
    if to_time is not None and to_time < from_time:
        raise ValueError("invalid_time_range")

    if cue_file.exists():
        # No range means "clear all" by deleting the cue file.
        if from_time <= 0.0 and to_time is None:
            cue_file.unlink()
            return

        with open(cue_file, "r") as f:
            raw = json.load(f)

        if not isinstance(raw, list):
            raw = []

        def _in_clear_window(item: Any) -> bool:
            if not isinstance(item, dict):
                return False
            try:
                entry_time = float(item.get("time", 0.0))
            except (TypeError, ValueError):
                return False
            if entry_time < from_time:
                return False
            if to_time is None:
                return True
            return entry_time <= to_time

        remaining = [item for item in raw if not _in_clear_window(item)]

        if not remaining:
            cue_file.unlink()
            return

        with open(cue_file, "w") as f:
            json.dump(_round_floats_for_save(remaining), f, indent=2)


def _cue_sort_key(entry: CueEntry) -> tuple[float, str, str]:
    label = entry.chaser_id or entry.fixture_id or ""
    effect = entry.effect or ""
    return (entry.time, label, effect)


def _is_same_identity(left: CueEntry, right: CueEntry) -> bool:
    if bool(left.chaser_id) != bool(right.chaser_id):
        return False
    if left.chaser_id:
        return left.chaser_id == right.chaser_id
    return left.fixture_id == right.fixture_id and left.effect == right.effect


def _find_duplicate_index(entries: List[CueEntry], candidate: CueEntry) -> Optional[int]:
    for index, entry in enumerate(entries):
        if not _is_same_identity(entry, candidate):
            continue
        if abs(float(entry.time) - float(candidate.time)) <= DUPLICATE_WINDOW_SECONDS:
            return index
    return None


def _dedupe_entries(entries: List[CueEntry]) -> List[CueEntry]:
    deduped: List[CueEntry] = []
    for entry in entries:
        duplicate_index = _find_duplicate_index(deduped, entry)
        if duplicate_index is not None:
            deduped[duplicate_index] = entry
            continue
        deduped.append(entry)
    deduped.sort(key=_cue_sort_key)
    return deduped


def _clean_cue_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    entry = CueEntry(**payload)
    return entry.model_dump(exclude_none=True)


def _merge_cue_payload(current: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    merged = {**current, **payload}
    next_chaser_id = str(merged.get("chaser_id") or "").strip()
    next_fixture_id = str(merged.get("fixture_id") or "").strip()
    next_effect = str(merged.get("effect") or "").strip()
    if next_chaser_id:
        merged.pop("fixture_id", None)
        merged.pop("effect", None)
        merged.pop("duration", None)
    elif next_fixture_id or next_effect or merged.get("duration") is not None:
        merged.pop("chaser_id", None)
    return _clean_cue_payload(merged)


def create_cue_entry(cue_sheet: CueSheet, payload: Dict[str, Any]) -> CueEntry:
    entry = CueEntry(**_clean_cue_payload(payload))
    duplicate_index = _find_duplicate_index(cue_sheet.entries, entry)
    if duplicate_index is not None:
        cue_sheet.entries[duplicate_index] = entry
    else:
        cue_sheet.entries.append(entry)
    cue_sheet.entries.sort(key=_cue_sort_key)
    return entry


def read_cue_entries(cue_sheet: CueSheet) -> List[Dict[str, Any]]:
    return [entry.model_dump(exclude_none=True) for entry in cue_sheet.entries]


def update_cue_entry(cue_sheet: CueSheet, index: int, payload: Dict[str, Any]) -> CueEntry:
    if index < 0 or index >= len(cue_sheet.entries):
        raise IndexError("cue_index_out_of_range")
    current = cue_sheet.entries[index].model_dump(exclude_none=True)
    updated = CueEntry(**_merge_cue_payload(current, payload))
    cue_sheet.entries[index] = updated
    cue_sheet.entries.sort(key=_cue_sort_key)
    return updated


def delete_cue_entry(cue_sheet: CueSheet, index: int) -> CueEntry:
    if index < 0 or index >= len(cue_sheet.entries):
        raise IndexError("cue_index_out_of_range")
    return cue_sheet.entries.pop(index)


def upsert_cue_entries(cue_sheet: CueSheet, new_entries: List[Dict[str, Any]]) -> Dict[str, int]:
    """Upsert cue entries by (time, fixture_id) key.

    Replaces existing entries with matching time+fixture_id, inserts new ones.
    Returns counts of generated, replaced, and skipped entries.
    """
    generated = 0
    replaced = 0
    skipped = 0

    for new_payload in new_entries:
        new_entry = CueEntry(**_clean_cue_payload(new_payload))
        duplicate_index = _find_duplicate_index(cue_sheet.entries, new_entry)

        if duplicate_index is not None:
            index = duplicate_index
            cue_sheet.entries[index] = new_entry
            replaced += 1
        else:
            cue_sheet.entries.append(new_entry)
            generated += 1

    cue_sheet.entries = _dedupe_entries(cue_sheet.entries)

    return {
        "generated": generated,
        "replaced": replaced,
        "skipped": skipped,
    }
