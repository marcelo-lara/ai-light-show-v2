from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import CueEntry, CueSheet


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
    entries = [entry.model_dump() for entry in cue_sheet.entries]
    with open(cue_file, "w") as f:
        json.dump(entries, f, indent=2)


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
