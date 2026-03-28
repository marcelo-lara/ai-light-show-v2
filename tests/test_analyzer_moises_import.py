import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analyzer"))

import analyze_song


def test_run_beat_finder_uses_moises_mix_data(tmp_path: Path, monkeypatch, capsys):
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
    ]))

    monkeypatch.setattr(
        analyze_song,
        "find_beats_and_downbeats",
        lambda song_path: (_ for _ in ()).throw(AssertionError("analyzer beat finder should not run")),
    )

    result = analyze_song.run_beat_finder_for(song_path, meta_path=meta_root)

    beats_payload = json.loads((meta_root / "Test Song" / "beats.json").read_text())
    info_payload = json.loads((meta_root / "Test Song" / "info.json").read_text())
    assert result == {"method": "moises", "beat_count": 2}
    assert beats_payload == [
        {"time": 1.001, "beat": 1, "bar": 1, "bass": "F", "chord": "Fm", "type": "downbeat"},
        {"time": 1.5, "beat": 2, "bar": 1, "bass": None, "chord": None, "type": "beat"},
    ]
    assert info_payload["beats_source"] == "moises"
    assert info_payload["artifacts"]["chords_file"].endswith("/Test Song/moises/chords.json")
    assert "Using Moises mix data for beats and chords" in capsys.readouterr().out


def test_run_beat_finder_falls_back_without_moises_chords(tmp_path: Path, monkeypatch):
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    moises_dir = meta_root / "Test Song" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "beats.json").write_text(json.dumps([
        {"time": 1.0, "beatNum": 1},
    ]))

    monkeypatch.setattr(
        analyze_song,
        "find_beats_and_downbeats",
        lambda song_path: {"beats": [1.0, 1.5], "downbeats": [1.0]},
    )

    result = analyze_song.run_beat_finder_for(song_path, meta_path=meta_root)

    beats_payload = json.loads((meta_root / "Test Song" / "beats.json").read_text())
    assert result == {"beats": [1.0, 1.5], "downbeats": [1.0]}
    assert beats_payload == [
        {"time": 1.0, "beat": 1, "bar": 1, "bass": None, "chord": None, "type": "downbeat"},
        {"time": 1.5, "beat": 2, "bar": 1, "bass": None, "chord": None, "type": "beat"},
    ]