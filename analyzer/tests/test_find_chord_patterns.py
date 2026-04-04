from __future__ import annotations

import json
from pathlib import Path

from src.musical_structure.chord_patterns import find_chord_patterns
from src.tasks.find_chord_patterns import run as run_find_chord_patterns


def _beats(patterns: list[list[str | None]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    time_value = 0.0
    for bar_number, beats in enumerate(patterns, start=1):
        for beat_number, chord in enumerate(beats, start=1):
            rows.append({"time": round(time_value, 3), "bar": bar_number, "beat": beat_number, "chord": chord, "type": "downbeat" if beat_number == 1 else "beat"})
            time_value += 0.5
    return rows


def test_find_chord_patterns_prefers_four_bar_windows_and_normalizes_sevenths() -> None:
    beats = _beats(
        [
            ["Cm", "Cm", "Cm", "Cm"],
            ["Fm7", "Fm7", "Fm7", "Fm7"],
            ["Cm", "Cm", "Cm", "Cm"],
            ["Fm", "Fm", "Fm", "Fm"],
            ["Cm", "Cm", "Cm", "Cm"],
            ["Fm", "Fm", "Fm", "Fm"],
            ["Cm", "Cm", "Cm", "Cm"],
            ["Fm", "Fm", "Fm", "Fm"],
            ["G", "G", "G", "G"],
            ["Am", "Am", "Am", "Am"],
            ["G", "G", "G", "G"],
            ["Am", "Am", "Am", "Am"],
            ["G", "G", "G", "G"],
            ["Am", "Am", "Am", "Am"],
            ["G", "G", "G", "G"],
            ["Am", "Am", "Am", "Bdim"],
        ]
    )

    payload = find_chord_patterns(beats, beats_file="/tmp/beats.json")

    assert payload is not None
    assert payload["patterns"][0]["bar_count"] == 4
    assert payload["patterns"][0]["sequence"] == "Cm|Fm|Cm|Fm"
    assert payload["patterns"][1]["sequence"] == "G|Am|G|Am"
    assert any(item["mismatch_count"] == 1 for item in payload["patterns"][1]["occurrences"])


def test_find_chord_patterns_task_writes_artifact_and_skips_cleanly(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_path = tmp_path / "meta"
    beats_dir = meta_path / "Alpha" / "reference"
    beats_dir.mkdir(parents=True)
    beats_file = beats_dir / "beats.json"
    beats_file.write_text(json.dumps(_beats([["Cm", "Cm", "Cm", "Cm"], ["Fm", "Fm", "Fm", "Fm"], ["Cm", "Cm", "Cm", "Cm"], ["Fm", "Fm", "Fm", "Fm"]])), encoding="utf-8")

    result = run_find_chord_patterns({"song_path": str(song_path), "meta_path": str(meta_path)})

    assert result["status"] == "completed"
    info = json.loads((meta_path / "Alpha" / "info.json").read_text(encoding="utf-8"))
    assert (meta_path / "Alpha" / "chord_patterns.json").exists()
    assert info["artifacts"]["chord_patterns_file"].endswith("Alpha/chord_patterns.json")

    empty_song = tmp_path / "songs" / "Beta.mp3"
    empty_song.touch()
    empty_dir = meta_path / "Beta" / "reference"
    empty_dir.mkdir(parents=True)
    (empty_dir / "beats.json").write_text(json.dumps(_beats([[None, None, None, None], [None, None, None, None]])), encoding="utf-8")

    skipped = run_find_chord_patterns({"song_path": str(empty_song), "meta_path": str(meta_path)})

    assert skipped["status"] == "skipped"
    assert not (meta_path / "Beta" / "chord_patterns.json").exists()
    assert not (meta_path / "Beta" / "info.json").exists()