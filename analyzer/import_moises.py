from __future__ import annotations

import json
import os
import sys
from pathlib import Path

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


def _build_chord_lookup(chord_rows: list[dict]) -> dict[float, list[dict]]:
    by_time: dict[float, list[dict]] = {}
    for row in chord_rows:
        time_value = _float_or_none(row.get("curr_beat_time"))
        if time_value is None:
            continue
        by_time.setdefault(time_value, []).append(row)
    return by_time


def _match_chord_row(chord_rows: list[dict], by_time: dict[float, list[dict]], beat_time: float, index: int) -> dict | None:
    if index < len(chord_rows):
        candidate = chord_rows[index]
        candidate_time = _float_or_none(candidate.get("curr_beat_time"))
        if candidate_time is not None and abs(candidate_time - beat_time) <= 0.05:
            return candidate
    matches = by_time.get(beat_time)
    if matches:
        return matches.pop(0)
    return None


def _fill_missing_bars(beats: list[dict]) -> None:
    if not beats or all(row.get("bar") is not None for row in beats):
        return
    current_bar = 1 if beats[0]["beat"] == 1 else 0
    for index, row in enumerate(beats):
        if row.get("bar") is None:
            if index > 0 and row["beat"] == 1:
                current_bar += 1
            row["bar"] = current_bar
        else:
            current_bar = int(row["bar"])


def import_moises(song_id: str, meta_path: str | Path = META_PATH) -> list[dict]:
    song_meta_dir = Path(meta_path).expanduser().resolve() / song_id
    moises_dir = song_meta_dir / "moises"
    beats_path = moises_dir / "beats.json"
    chords_path = moises_dir / "chords.json"
    output_path = song_meta_dir / "beats.json"

    beat_rows = _load_rows(beats_path)
    chord_rows = _load_rows(chords_path)
    if not beat_rows and not chord_rows:
        print(f"ERROR: no usable Moises mix data found in {moises_dir}")
        return []

    by_time = _build_chord_lookup(chord_rows)
    source_rows = beat_rows or chord_rows
    normalized: list[dict] = []
    previous_beat = 0
    for index, row in enumerate(source_rows):
        time_value = _float_or_none(row.get("time") if beat_rows else row.get("curr_beat_time"))
        if time_value is None:
            continue
        chord_row = _match_chord_row(chord_rows, by_time, time_value, index) if chord_rows else None
        beat_value = _int_or_none(row.get("beatNum") if beat_rows else row.get("beat_num"))
        if beat_value is None and chord_row is not None:
            beat_value = _int_or_none(chord_row.get("beat_num"))
        if beat_value is None:
            beat_value = 1 if previous_beat in {0, 4} else previous_beat + 1
        previous_beat = beat_value
        normalized.append(
            {
                "time": time_value,
                "beat": beat_value,
                "bar": _int_or_none(chord_row.get("bar_num")) if chord_row is not None else None,
                "bass": chord_row.get("bass") if chord_row and chord_row.get("bass") else None,
                "chord": chord_row.get("chord_basic_pop") if chord_row and chord_row.get("chord_basic_pop") else None,
            }
        )

    _fill_missing_bars(normalized)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=2)
    print(f"Successfully normalized {len(normalized)} Moises beat rows to {output_path}")
    return normalized


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_moises.py <song_id>")
    else:
        import_moises(sys.argv[1])
