import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analyzer"))

import analyze_song


def test_analyze_all_songs_runs_requested_steps_in_order(tmp_path: Path, monkeypatch):
    songs_dir = tmp_path / "songs"
    songs_dir.mkdir()
    plain_song = songs_dir / "Alpha.mp3"
    moises_song = songs_dir / "Beta.mp3"
    plain_song.touch()
    moises_song.touch()

    meta_root = tmp_path / "meta"
    moises_dir = meta_root / "Beta" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "beats.json").write_text(json.dumps([{"time": 1.0, "beatNum": 1}]))

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(analyze_song, "autodetect_device", lambda: "cpu")
    monkeypatch.setattr(
        analyze_song,
        "run_split_stems_for",
        lambda song_path, device, meta_path=analyze_song.META_PATH: calls.append((song_path.stem, "split_stems")),
    )
    monkeypatch.setattr(
        analyze_song,
        "run_beat_finder_for",
        lambda song_path, meta_path=analyze_song.META_PATH: calls.append((song_path.stem, "beat_finder")),
    )
    monkeypatch.setattr(
        analyze_song,
        "run_essentia_analysis_for",
        lambda song_path, meta_path=analyze_song.META_PATH: calls.append((song_path.stem, "essentia_analysis")),
    )
    monkeypatch.setattr(
        analyze_song,
        "run_import_moises_for",
        lambda song_path, meta_path=analyze_song.META_PATH: calls.append((song_path.stem, "import_moises")),
    )
    monkeypatch.setattr(
        analyze_song,
        "run_generate_md_for",
        lambda song_path, meta_path=analyze_song.META_PATH: calls.append((song_path.stem, "generate_md")),
    )

    results = analyze_song.analyze_all_songs(songs_dir=songs_dir, meta_path=meta_root, device="cpu")

    assert calls == [
        ("Alpha", "split_stems"),
        ("Alpha", "beat_finder"),
        ("Alpha", "essentia_analysis"),
        ("Alpha", "generate_md"),
        ("Beta", "split_stems"),
        ("Beta", "essentia_analysis"),
        ("Beta", "import_moises"),
        ("Beta", "generate_md"),
    ]
    assert results == [
        {"song": "Alpha.mp3", "steps": ["split_stems", "beat_finder", "essentia_analysis", "generate_md"], "status": "completed"},
        {"song": "Beta.mp3", "steps": ["split_stems", "essentia_analysis", "import_moises", "generate_md"], "status": "completed"},
    ]