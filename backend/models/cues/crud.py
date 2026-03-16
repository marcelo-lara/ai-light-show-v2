from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import CueEntry, CueSheet


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
    entries = [_round_floats_for_save(entry.model_dump()) for entry in cue_sheet.entries]
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

def create_cue_entry(cue_sheet: CueSheet, payload: Dict[str, Any]) -> CueEntry:
    entry = CueEntry(**payload)
    cue_sheet.entries.append(entry)
    cue_sheet.entries.sort(key=lambda e: (e.time, e.fixture_id, e.effect))
    return entry


def read_cue_entries(cue_sheet: CueSheet) -> List[Dict[str, Any]]:
    return [entry.model_dump() for entry in cue_sheet.entries]


def update_cue_entry(cue_sheet: CueSheet, index: int, payload: Dict[str, Any]) -> CueEntry:
    if index < 0 or index >= len(cue_sheet.entries):
        raise IndexError("cue_index_out_of_range")
    current = cue_sheet.entries[index].model_dump()
    updated = CueEntry(**{**current, **payload})
    cue_sheet.entries[index] = updated
    cue_sheet.entries.sort(key=lambda e: (e.time, e.fixture_id, e.effect))
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
    # Create a lookup map for existing entries by (time, fixture_id)
    existing_map: Dict[tuple[float, str], int] = {}
    for i, entry in enumerate(cue_sheet.entries):
        key = (round(entry.time, 6), entry.fixture_id)  # Normalize time to avoid float precision issues
        existing_map[key] = i

    generated = 0
    replaced = 0
    skipped = 0

    for new_payload in new_entries:
        new_entry = CueEntry(**new_payload)
        key = (round(new_entry.time, 6), new_entry.fixture_id)

        if key in existing_map:
            # Replace existing entry
            index = existing_map[key]
            cue_sheet.entries[index] = new_entry
            replaced += 1
        else:
            # Insert new entry
            cue_sheet.entries.append(new_entry)
            generated += 1

    # Re-sort all entries after modifications
    cue_sheet.entries.sort(key=lambda e: (e.time, e.fixture_id, e.effect))

    return {
        "generated": generated,
        "replaced": replaced,
        "skipped": skipped,
    }
