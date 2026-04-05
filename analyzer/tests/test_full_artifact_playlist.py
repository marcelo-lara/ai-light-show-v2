from __future__ import annotations

import json
from pathlib import Path

from src.playlists.full_artifact import build_full_artifact_playlist, execute_full_artifact_playlist


def test_build_full_artifact_playlist_for_analyzer_song(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()

    playlist = build_full_artifact_playlist(song_path, tmp_path / "meta", device="cpu")

    assert playlist["playlist"] == "full-artifact-analyzer"
    assert [item["task_type"] for item in playlist["tasks"]] == [
        "init-song",
        "split-stems",
        "beat-finder",
        "find_chords",
        "find_sections",
        "essentia-analysis",
        "find-song-features",
        "stereo-analysis",
        "find-chord-patterns",
        "find-stem-patterns",
        "harmonic-layer",
        "symbolic-layer",
        "energy-layer",
        "build-music-feature-layers",
        "generate-md",
    ]


def test_build_full_artifact_playlist_for_moises_song(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Beta.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    moises_dir = tmp_path / "meta" / "Beta" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "chords.json").write_text(json.dumps([{"curr_beat_time": 1.0, "beat_num": 1, "bar_num": 1, "bass": "C", "chord_basic_pop": "C"}]), encoding="utf-8")
    (moises_dir / "segments.json").write_text(json.dumps([{"start": 0.0, "end": 4.0, "label": "Intro"}]), encoding="utf-8")

    playlist = build_full_artifact_playlist(song_path, tmp_path / "meta", device="cpu")

    assert playlist["playlist"] == "full-artifact-moises"
    assert [item["task_type"] for item in playlist["tasks"]] == [
        "init-song",
        "split-stems",
        "import-moises",
        "essentia-analysis",
        "find-song-features",
        "stereo-analysis",
        "find-chord-patterns",
        "find-stem-patterns",
        "harmonic-layer",
        "symbolic-layer",
        "energy-layer",
        "build-music-feature-layers",
        "generate-md",
    ]


def test_build_full_artifact_playlist_for_moises_song_without_segments(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Gamma.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    moises_dir = tmp_path / "meta" / "Gamma" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "chords.json").write_text(json.dumps([{"curr_beat_time": 1.0, "beat_num": 1, "bar_num": 1, "bass": "C", "chord_basic_pop": "C"}]), encoding="utf-8")

    playlist = build_full_artifact_playlist(song_path, tmp_path / "meta", device="cpu")

    assert [item["task_type"] for item in playlist["tasks"]] == [
        "init-song",
        "split-stems",
        "import-moises",
        "find_sections",
        "essentia-analysis",
        "find-song-features",
        "stereo-analysis",
        "find-chord-patterns",
        "find-stem-patterns",
        "harmonic-layer",
        "symbolic-layer",
        "energy-layer",
        "build-music-feature-layers",
        "generate-md",
    ]


def test_execute_full_artifact_playlist_stops_on_failure(monkeypatch, tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    calls: list[str] = []

    def fake_run(task_type: str, params: dict[str, str], progress_callback=None):
        del params, progress_callback
        calls.append(task_type)
        if task_type == "find_sections":
            return None
        return {"task": task_type}

    monkeypatch.setattr("src.playlists.full_artifact.run_registered_task", fake_run)

    result = execute_full_artifact_playlist(song_path, tmp_path / "meta", device="cpu")

    assert result["status"] == "failed"
    assert calls == ["init-song", "split-stems", "beat-finder", "find_chords", "find_sections"]


def test_import_moises_preserves_source_files(tmp_path: Path) -> None:
    from src.task_queue.dispatch import run_task

    song_path = tmp_path / "songs" / "Beta.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    moises_dir = tmp_path / "meta" / "Beta" / "moises"
    moises_dir.mkdir(parents=True)
    chords_payload = [{"curr_beat_time": 1.0, "beat_num": 1, "bar_num": 1, "bass": "C", "chord_basic_pop": "C"}]
    chords_path = moises_dir / "chords.json"
    chords_path.write_text(json.dumps(chords_payload, indent=2), encoding="utf-8")

    result = run_task("import-moises", {"song_path": str(song_path), "meta_path": str(tmp_path / "meta")})

    assert result["ok"] is True
    assert json.loads(chords_path.read_text(encoding="utf-8")) == chords_payload