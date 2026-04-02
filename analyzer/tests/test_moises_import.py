from __future__ import annotations

import json
from pathlib import Path

import analyze_song
from src.tasks import find_beats as find_beats_task_module
from src.moises.sections_from_segments import validate_sections_rows


def test_run_beat_finder_uses_moises_mix_data(tmp_path: Path, monkeypatch, capsys) -> None:
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    moises_dir = meta_root / "Test Song" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "chords.json").write_text(json.dumps([
        {"curr_beat_time": 1.001, "beat_num": 1, "bar_num": 1, "bass": "F", "chord_basic_pop": "Fm"},
        {"curr_beat_time": 1.4999, "beat_num": 2, "bar_num": 1, "bass": None, "chord_basic_pop": "N"},
        {"curr_beat_time": "bad", "beat_num": 3, "bar_num": 1, "bass": "A", "chord_basic_pop": "Am"},
    ]), encoding="utf-8")

    monkeypatch.setattr(find_beats_task_module, "find_beats_and_downbeats", lambda song_path: (_ for _ in ()).throw(AssertionError("analyzer beat finder should not run")))

    result = analyze_song.run_beat_finder_for(song_path, meta_path=meta_root)

    beats_payload = json.loads((meta_root / "Test Song" / "beats.json").read_text(encoding="utf-8"))
    info_payload = json.loads((meta_root / "Test Song" / "info.json").read_text(encoding="utf-8"))
    assert result is not None
    assert result["method"] == "moises"
    assert result["beat_count"] == 2
    assert result["beats_file"].endswith("/Test Song/beats.json")
    assert beats_payload == [
        {"time": 1.001, "beat": 1, "bar": 1, "bass": "F", "chord": "Fm", "type": "downbeat"},
        {"time": 1.5, "beat": 2, "bar": 1, "bass": None, "chord": None, "type": "beat"},
    ]
    assert info_payload["beats_source"] == "moises"
    assert info_payload["artifacts"]["chords_file"].endswith("/Test Song/moises/chords.json")
    assert "Using Moises mix data for beats and chords" in capsys.readouterr().out


def test_run_beat_finder_falls_back_without_moises_chords(tmp_path: Path, monkeypatch) -> None:
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    moises_dir = meta_root / "Test Song" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "beats.json").write_text(json.dumps([{"time": 1.0, "beatNum": 1}]), encoding="utf-8")

    monkeypatch.setattr(find_beats_task_module, "find_beats_and_downbeats", lambda song_path: {"beats": [1.0, 1.5], "downbeats": [1.0]})

    result = analyze_song.run_beat_finder_for(song_path, meta_path=meta_root)

    beats_payload = json.loads((meta_root / "Test Song" / "beats.json").read_text(encoding="utf-8"))
    assert result is not None
    assert result["beats"] == [1.0, 1.5]
    assert result["downbeats"] == [1.0]
    assert result["beats_file"].endswith("/Test Song/beats.json")
    assert beats_payload == [
        {"time": 1.0, "beat": 1, "bar": 1, "bass": None, "chord": None, "type": "downbeat"},
        {"time": 1.5, "beat": 2, "bar": 1, "bass": None, "chord": None, "type": "beat"},
    ]


def test_validate_sections_rows_matches_backend_rules() -> None:
    sections_rows = [
        {"start": 1.36, "end": 35.82, "label": "Intro", "description": "", "hints": []},
        {"start": 35.82, "end": 50.14, "label": "Instrumental", "description": "", "hints": []},
    ]

    assert validate_sections_rows(sections_rows) == (True, "ok")

    from backend.store.services.section_persistence import normalize_sections_input

    is_valid, details = normalize_sections_input(
        [{"name": row["label"], "start": row["start"], "end": row["end"]} for row in sections_rows]
    )
    assert is_valid, details


def test_run_import_moises_generates_sections_from_segments(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    moises_dir = meta_root / "Test Song" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "chords.json").write_text(json.dumps([
        {"curr_beat_time": 1.0, "beat_num": 1, "bar_num": 1, "bass": "F", "chord_basic_pop": "Fm"},
    ]), encoding="utf-8")
    (moises_dir / "segments.json").write_text(json.dumps([
        {"start": 1.36, "end": 35.82, "label": "Intro"},
        {"start": 35.82, "end": 50.14, "label": "Instrumental"},
    ]), encoding="utf-8")

    analyze_song.run_import_moises_for(song_path, meta_path=meta_root)

    sections_payload = json.loads((meta_root / "Test Song" / "sections.json").read_text(encoding="utf-8"))
    assert sections_payload == [
        {"start": 1.36, "end": 35.82, "label": "Intro", "description": "", "hints": []},
        {"start": 35.82, "end": 50.14, "label": "Instrumental", "description": "", "hints": []},
    ]


def test_run_import_moises_preserves_existing_sections(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_meta_dir = meta_root / "Test Song"
    moises_dir = song_meta_dir / "moises"
    moises_dir.mkdir(parents=True)
    existing_sections = [{"start": 1.36, "end": 35.82, "label": "Intro", "description": "Existing authored copy.", "hints": [{"start": 10.0, "end": 12.0, "hint": "Keep this."}]}]
    (song_meta_dir / "sections.json").write_text(json.dumps(existing_sections), encoding="utf-8")
    (moises_dir / "chords.json").write_text(json.dumps([
        {"curr_beat_time": 1.0, "beat_num": 1, "bar_num": 1, "bass": "F", "chord_basic_pop": "Fm"},
    ]), encoding="utf-8")
    (moises_dir / "segments.json").write_text(json.dumps([
        {"start": 1.36, "end": 35.82, "label": "Intro"},
        {"start": 35.82, "end": 50.14, "label": "Instrumental"},
    ]), encoding="utf-8")

    analyze_song.run_import_moises_for(song_path, meta_path=meta_root)

    assert json.loads((song_meta_dir / "sections.json").read_text(encoding="utf-8")) == existing_sections


def test_run_import_moises_skips_invalid_segment_ranges(tmp_path: Path, capsys) -> None:
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    moises_dir = meta_root / "Test Song" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "chords.json").write_text(json.dumps([
        {"curr_beat_time": 1.0, "beat_num": 1, "bar_num": 1, "bass": "F", "chord_basic_pop": "Fm"},
    ]), encoding="utf-8")
    (moises_dir / "segments.json").write_text(json.dumps([
        {"start": 1.36, "end": 35.82, "label": "Intro"},
        {"start": 30.0, "end": 50.14, "label": "Instrumental"},
    ]), encoding="utf-8")

    analyze_song.run_import_moises_for(song_path, meta_path=meta_root)

    assert not (meta_root / "Test Song" / "sections.json").exists()
    assert "failed section validation" in capsys.readouterr().out