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

    def fake_analyze(audio_path: str, out_dir: str, part_name: str, sample_rate: int = 44100, artifact_file_stems=None):
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
    assert (essentia_dir / "loudness_envelope.bass.json").exists()
    assert (essentia_dir / "loudness_envelope.bass.svg").exists()
    assert (essentia_dir / "loudness_envelope.drums.svg").exists()
    assert essentia_artifacts["loudness_envelope"]["json"].endswith("/loudness_envelope.json")
    assert essentia_artifacts["loudness_envelope"]["svg"].endswith("/loudness_envelope.svg")
    assert essentia_artifacts["bass_loudness_envelope"]["json"].endswith("/loudness_envelope.bass.json")
    assert essentia_artifacts["bass_loudness_envelope"]["svg"].endswith("/loudness_envelope.bass.svg")
    assert essentia_artifacts["drums_loudness_envelope"]["json"].endswith("/loudness_envelope.drums.json")
    assert essentia_artifacts["drums_loudness_envelope"]["svg"].endswith("/loudness_envelope.drums.svg")