from __future__ import annotations

import json
from pathlib import Path

import analyze_song


def test_analyze_all_songs_runs_requested_steps_in_order(tmp_path: Path, monkeypatch) -> None:
    songs_dir = tmp_path / "songs"
    songs_dir.mkdir()
    plain_song = songs_dir / "Alpha.mp3"
    moises_song = songs_dir / "Beta.mp3"
    plain_song.touch()
    moises_song.touch()

    meta_root = tmp_path / "meta"
    moises_dir = meta_root / "Beta" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "beats.json").write_text(json.dumps([{"time": 1.0, "beatNum": 1}]), encoding="utf-8")

    calls: list[str] = []
    monkeypatch.setattr(analyze_song, "autodetect_device", lambda: "cpu")

    def fake_playlist(song_path: Path, meta_path: str | Path = analyze_song.META_PATH, device: str | None = None, progress_callback=None):
        calls.append(song_path.stem)
        if song_path.stem == "Alpha":
            return {
                "status": "completed",
                "results": [
                    {"task_type": "init-song"},
                    {"task_type": "split-stems"},
                    {"task_type": "beat-finder"},
                    {"task_type": "find_sections"},
                    {"task_type": "essentia-analysis"},
                    {"task_type": "find-song-features"},
                    {"task_type": "generate-md"},
                ],
            }
        return {
            "status": "completed",
            "results": [
                {"task_type": "init-song"},
                {"task_type": "split-stems"},
                {"task_type": "import-moises"},
                {"task_type": "essentia-analysis"},
                {"task_type": "find-song-features"},
                {"task_type": "generate-md"},
            ],
        }

    monkeypatch.setattr(analyze_song, "run_full_artifact_playlist_for", fake_playlist)

    results = analyze_song.analyze_all_songs(songs_dir=songs_dir, meta_path=meta_root, device="cpu")

    assert calls == ["Alpha", "Beta"]
    assert results == [
        {"song": "Alpha.mp3", "steps": ["init-song", "split-stems", "beat-finder", "find_sections", "essentia-analysis", "find-song-features", "generate-md"], "status": "completed"},
        {"song": "Beta.mp3", "steps": ["init-song", "split-stems", "import-moises", "essentia-analysis", "find-song-features", "generate-md"], "status": "completed"},
    ]