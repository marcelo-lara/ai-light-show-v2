from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .sections_from_segments import generate_sections_from_segments

META_PATH = os.environ.get("META_PATH", "/app/meta")


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


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_chord_row(row: dict) -> dict | None:
    time_value = _float_or_none(row.get("curr_beat_time"))
    beat_value = _int_or_none(row.get("beat_num"))
    bar_value = _int_or_none(row.get("bar_num"))
    if time_value is None or beat_value is None or bar_value is None:
        return None
    bass_value = row.get("bass")
    chord_value = row.get("chord_basic_pop")
    normalized_chord = None if chord_value in {None, "N"} else chord_value
    return {
        "time": time_value,
        "beat": beat_value,
        "bar": bar_value,
        "bass": bass_value if bass_value else None,
        "chord": normalized_chord,
        "type": "downbeat" if beat_value == 1 else "beat",
    }


def import_moises(song_id: str, meta_path: str | Path = META_PATH) -> list[dict]:
    song_meta_dir = Path(meta_path).expanduser().resolve() / song_id
    moises_dir = song_meta_dir / "moises"
    chords_path = moises_dir / "chords.json"
    output_path = song_meta_dir / "beats.json"

    chord_rows = _load_rows(chords_path)
    if not chord_rows:
        print(f"ERROR: no usable Moises chord data found in {moises_dir}")
        return []

    normalized = [row for row in (_normalize_chord_row(chord_row) for chord_row in chord_rows) if row is not None]
    if not normalized:
        print(f"ERROR: no valid Moises chord rows found in {chords_path}")
        return []

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=2)
    print(f"Successfully normalized {len(normalized)} Moises chord rows to {output_path}")
    generate_sections_from_segments(song_meta_dir)
    return normalized


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_moises.py <song_id>")
    else:
        import_moises(sys.argv[1])
