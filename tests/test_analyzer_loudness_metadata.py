import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analyzer"))

import analyze_song


def test_run_essentia_analysis_registers_dotted_stem_loudness_files(tmp_path: Path, monkeypatch):
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    stems_dir = tmp_path / "stems"
    stems_dir.mkdir()
    stems = []
    for stem_name in ["bass", "drums", "vocals", "other"]:
        stem_file = stems_dir / f"{stem_name}.wav"
        stem_file.touch()
        stems.append(str(stem_file))
    song_meta_dir = meta_root / "Test Song"
    song_meta_dir.mkdir(parents=True)
    (song_meta_dir / "info.json").write_text(json.dumps({"stems_dir": str(stems_dir), "stems": stems}))

    def fake_analyze(
        audio_path: str,
        out_dir: str,
        part_name: str,
        sample_rate: int = 44100,
        artifact_file_stems=None,
        progress_callback=None,
    ):
        artifact_file_stems = artifact_file_stems or {}
        for artifact_name in ["rhythm", "loudness_envelope"]:
            file_stem = artifact_file_stems.get(artifact_name, artifact_name)
            (Path(out_dir) / f"{file_stem}.json").write_text("{}")
            (Path(out_dir) / f"{file_stem}.svg").write_text("<svg />")
        return {"rhythm": {"rhythm": {"bpm": 120.0}}, "loudness_envelope": {"part": part_name}}

    monkeypatch.setattr(analyze_song, "analyze_with_essentia", fake_analyze)
    monkeypatch.setattr(analyze_song, "is_stem_worth_analyzing", lambda audio_path: True)
    monkeypatch.setattr(analyze_song, "autodetect_device", lambda: "cpu")

    analyze_song.run_essentia_analysis_for(song_path, meta_path=meta_root)

    essentia_dir = song_meta_dir / "essentia"
    info_payload = json.loads((song_meta_dir / "info.json").read_text())
    essentia_artifacts = info_payload["artifacts"]["essentia"]
    assert (essentia_dir / "loudness_envelope.json").exists()
    assert (essentia_dir / "bass_loudness_envelope.json").exists()
    assert (essentia_dir / "bass_loudness_envelope.svg").exists()
    assert (essentia_dir / "drums_loudness_envelope.svg").exists()
    assert essentia_artifacts["mix"]["loudness_envelope"]["json"].endswith("/loudness_envelope.json")
    assert essentia_artifacts["mix"]["loudness_envelope"]["svg"].endswith("/loudness_envelope.svg")
    assert essentia_artifacts["bass"]["loudness_envelope"]["json"].endswith("/bass_loudness_envelope.json")
    assert essentia_artifacts["bass"]["loudness_envelope"]["svg"].endswith("/bass_loudness_envelope.svg")
    assert essentia_artifacts["drums"]["loudness_envelope"]["json"].endswith("/drums_loudness_envelope.json")
    assert essentia_artifacts["drums"]["loudness_envelope"]["svg"].endswith("/drums_loudness_envelope.svg")


def test_run_essentia_analysis_probes_sample_rate_before_analysis(tmp_path: Path, monkeypatch):
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_meta_dir = meta_root / "Test Song"
    song_meta_dir.mkdir(parents=True)
    (song_meta_dir / "info.json").write_text(json.dumps({}))

    captured_calls: list[tuple[str, int | None]] = []

    def fake_analyze(
        audio_path: str,
        out_dir: str,
        part_name: str,
        sample_rate: int | None = None,
        artifact_file_stems=None,
        progress_callback=None,
    ):
        captured_calls.append((part_name, sample_rate))
        artifact_file_stems = artifact_file_stems or {}
        for artifact_name in ["rhythm", "loudness_envelope"]:
            file_stem = artifact_file_stems.get(artifact_name, artifact_name)
            (Path(out_dir) / f"{file_stem}.json").write_text("{}")
            (Path(out_dir) / f"{file_stem}.svg").write_text("<svg />")
        return {"rhythm": {"rhythm": {"bpm": 120.0}}, "loudness_envelope": {"part": part_name}}

    monkeypatch.setattr(analyze_song, "analyze_with_essentia", fake_analyze)
    monkeypatch.setattr(analyze_song, "autodetect_device", lambda: "cpu")
    monkeypatch.setattr(analyze_song, "_read_sample_rate", lambda audio_path: 48000)

    analyze_song.run_essentia_analysis_for(song_path, meta_path=meta_root)

    assert captured_calls == [("mix", 48000)]


def test_run_essentia_analysis_emits_wrapper_and_part_progress(tmp_path: Path, monkeypatch):
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_meta_dir = meta_root / "Test Song"
    song_meta_dir.mkdir(parents=True)
    (song_meta_dir / "info.json").write_text(json.dumps({}))

    events: list[dict] = []

    def fake_analyze(
        audio_path: str,
        out_dir: str,
        part_name: str,
        sample_rate: int | None = None,
        artifact_file_stems=None,
        progress_callback=None,
    ):
        if progress_callback is not None:
            progress_callback(
                {
                    "task_type": "essentia-analysis",
                    "stage": "Loudness & Envelope",
                    "step_current": 6,
                    "step_total": 20,
                    "message": "essentia-analysis [6/20] Loudness & Envelope",
                    "part_name": part_name,
                }
            )
        artifact_file_stems = artifact_file_stems or {}
        for artifact_name in ["rhythm", "loudness_envelope"]:
            file_stem = artifact_file_stems.get(artifact_name, artifact_name)
            (Path(out_dir) / f"{file_stem}.json").write_text("{}")
            (Path(out_dir) / f"{file_stem}.svg").write_text("<svg />")
        return {"rhythm": {"rhythm": {"bpm": 120.0}}, "loudness_envelope": {"part": part_name}}

    monkeypatch.setattr(analyze_song, "analyze_with_essentia", fake_analyze)
    monkeypatch.setattr(analyze_song, "autodetect_device", lambda: "cpu")

    analyze_song.run_essentia_analysis_for(song_path, meta_path=meta_root, progress_callback=events.append)

    assert events[0]["stage"] == "Start"
    assert events[1]["stage"] == "Analyze Mix"
    assert events[2]["stage"] == "Loudness & Envelope"
    assert events[2]["part_name"] == "mix"
    assert events[-1]["stage"] == "Complete"