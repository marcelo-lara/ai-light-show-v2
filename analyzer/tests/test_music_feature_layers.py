from __future__ import annotations

import json
from pathlib import Path

from src.feature_layers.harmonic import build_harmonic_layer
from src.feature_layers.energy import build_energy_layer
from src.feature_layers.symbolic import build_symbolic_layer
from src.tasks.build_music_feature_layers import run as run_build_music_feature_layers
from src.tasks.energy_layer import run as run_energy_layer
from src.tasks.harmonic_layer import run as run_harmonic_layer
from src.tasks.symbolic_layer import run as run_symbolic_layer


def test_layer_tasks_and_ir_builder_write_expected_files(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_dir = meta_root / "Test Song"
    song_dir.mkdir(parents=True)
    (song_dir / "info.json").write_text(json.dumps({"song_name": "Test Song", "bpm": 120, "duration": 42, "song_key": "Am", "artifacts": {}}), encoding="utf-8")
    (song_dir / "sections.json").write_text(json.dumps([{"start": 0.0, "end": 10.0, "label": "Intro"}]), encoding="utf-8")
    (song_dir / "features.json").write_text(json.dumps({"global": {"energy": {"mean": 0.3, "peak": 1.1, "dynamic_range": 0.8, "volatility": 0.2}}, "sections": [{"name": "Intro", "start_s": 0.0, "energy": {"level": "low", "trend": "swell", "peak": 1.1}, "summary": "Intro holds back."}]}), encoding="utf-8")
    (song_dir / "hints.json").write_text(json.dumps([{"name": "Intro", "start_s": 0.0, "end_s": 10.0, "hints": [{"time_s": 2.0, "kind": "rise", "strength": 0.5, "parts": ["drums"]}]}]), encoding="utf-8")
    reference_dir = song_dir / "reference"
    reference_dir.mkdir()
    (reference_dir / "beats.json").write_text(json.dumps([{"time": 0.0, "bar": 1, "beat": 1, "type": "downbeat", "chord": "Am", "bass": "A"}]), encoding="utf-8")

    harmonic_result = run_harmonic_layer({"song_path": str(song_path), "meta_path": str(meta_root)})
    energy_result = run_energy_layer({"song_path": str(song_path), "meta_path": str(meta_root)})
    symbolic_file = song_dir / "layer_b_symbolic.json"
    symbolic_file.write_text(json.dumps({"schema_version": "1.0", "song_id": "Test Song", "generated_from": {}, "transcription_source": {"engine": "basic-pitch", "model_version": "unknown", "stems_used": ["mix"]}, "note_events": [], "symbolic_summary": {"texture": "sparse", "melodic_contour": "unknown", "bass_motion": "unknown", "repetition_level": "low", "density_trend": "unknown", "description": "No symbolic summary available."}, "density_per_bar": [], "phrase_contours": [], "bass_movement_events": [], "repeated_motifs": [], "section_symbolic": [], "validation_notes": ["Basic Pitch notes unavailable; symbolic layer contains empty note inventory."]}), encoding="utf-8")
    ir_result = run_build_music_feature_layers({"song_path": str(song_path), "meta_path": str(meta_root)})

    assert Path(harmonic_result["layer_a_harmonic_file"]).exists()
    assert Path(energy_result["layer_c_energy_file"]).exists()
    assert Path(ir_result["music_feature_layers_file"]).exists()

    ir_payload = json.loads(Path(ir_result["music_feature_layers_file"]).read_text(encoding="utf-8"))
    assert ir_payload["metadata"]["title"] == "Test Song"
    assert ir_payload["layers"]["harmonic"]["global_key"]["label"] == "Am"
    assert ir_payload["layers"]["energy"]["global_energy"]["energy_trend"] == "plateau"
    assert ir_payload["energy_profile"]["energy_trend"] == "plateau"
    assert "onset_count" in ir_payload["energy_profile"]
    assert ir_payload["section_cards"][0]["energy_profile"]["level"] == "low"


def test_symbolic_layer_uses_harmonic_and_bass_stems(monkeypatch, tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Test Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_dir = meta_root / "Test Song"
    song_dir.mkdir(parents=True)
    stems_dir = tmp_path / "stems"
    stems_dir.mkdir()
    bass = stems_dir / "bass.wav"
    other = stems_dir / "other.wav"
    bass.touch()
    other.touch()
    (song_dir / "info.json").write_text(json.dumps({"stems": [str(bass), str(other)]}), encoding="utf-8")
    (song_dir / "sections.json").write_text(json.dumps([{"start": 0.0, "end": 8.0, "label": "Intro"}]), encoding="utf-8")
    reference_dir = song_dir / "reference"
    reference_dir.mkdir()
    (reference_dir / "beats.json").write_text(json.dumps([{"time": 1.0, "bar": 1, "beat": 1, "type": "downbeat"}, {"time": 2.0, "bar": 1, "beat": 2, "type": "beat"}]), encoding="utf-8")

    monkeypatch.setattr(
        "src.tasks.symbolic_layer.transcribe_sources",
        lambda sources: [
            {"start_s": 1.05, "end_s": 1.30, "pitch_midi": 40, "pitch_name": "E2", "confidence": 0.8, "source_part": key}
            for key in sources.keys()
        ],
    )

    result = run_symbolic_layer({"song_path": str(song_path), "meta_path": str(meta_root)})

    payload = json.loads(Path(result["layer_b_symbolic_file"]).read_text(encoding="utf-8"))
    assert payload["transcription_source"]["stems_used"] == ["harmonic", "bass"]
    assert [note["source_part"] for note in payload["note_events"]] == ["harmonic", "bass"]
    assert all(note["bar_index"] == 1 for note in payload["note_events"])


def test_harmonic_layer_uses_hpcp_for_cadence_and_tension(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Cadence Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_dir = meta_root / "Cadence Song"
    song_dir.mkdir(parents=True)
    essentia_dir = song_dir / "essentia"
    essentia_dir.mkdir()
    (song_dir / "info.json").write_text(json.dumps({"song_name": "Cadence Song", "song_key": "C", "artifacts": {}}), encoding="utf-8")
    (song_dir / "sections.json").write_text(json.dumps([{"start": 0.0, "end": 4.0, "label": "Intro"}, {"start": 4.0, "end": 8.0, "label": "Hook"}]), encoding="utf-8")
    (song_dir / "features.json").write_text(json.dumps({"global": {"key": {"canonical": "C", "detected": {"strength": 0.71}}}}), encoding="utf-8")
    (essentia_dir / "other_chroma_hpcp.json").write_text(
        json.dumps(
            {
                "times": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
                "hpcp": [
                    [0.05, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 0.85, 0.0, 0.0, 0.0, 0.0],
                    [0.05, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 0.85, 0.0, 0.0, 0.0, 0.0],
                    [0.9, 0.0, 0.0, 0.0, 0.2, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0],
                    [0.9, 0.0, 0.0, 0.0, 0.2, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0],
                    [0.1, 0.0, 0.0, 0.0, 0.0, 0.85, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    [0.1, 0.0, 0.0, 0.0, 0.0, 0.85, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    [0.95, 0.0, 0.0, 0.0, 0.15, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0],
                    [0.95, 0.0, 0.0, 0.0, 0.15, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0],
                ],
            }
        ),
        encoding="utf-8",
    )
    reference_dir = song_dir / "reference"
    reference_dir.mkdir()
    (reference_dir / "beats.json").write_text(
        json.dumps(
            [
                {"time": 0.0, "bar": 1, "beat": 1, "type": "downbeat", "chord": "G"},
                {"time": 1.0, "bar": 1, "beat": 2, "type": "beat", "chord": "G"},
                {"time": 2.0, "bar": 2, "beat": 1, "type": "downbeat", "chord": "C"},
                {"time": 3.0, "bar": 2, "beat": 2, "type": "beat", "chord": "C"},
                {"time": 4.0, "bar": 3, "beat": 1, "type": "downbeat", "chord": "F"},
                {"time": 5.0, "bar": 3, "beat": 2, "type": "beat", "chord": "F"},
                {"time": 6.0, "bar": 4, "beat": 1, "type": "downbeat", "chord": "C"},
                {"time": 7.0, "bar": 4, "beat": 2, "type": "beat", "chord": "C"},
            ]
        ),
        encoding="utf-8",
    )

    payload = build_harmonic_layer(song_path, meta_root)

    assert payload["harmonic_summary"]["key_stability"] in {"stable", "centered"}
    assert payload["harmonic_summary"]["cadence_notes"][0]["type"] == "dominant_resolution"
    assert payload["section_harmony"][0]["cadence"]["type"] == "dominant_resolution"
    assert payload["section_harmony"][1]["cadence"]["type"] == "plagal_resolution"
    assert payload["section_harmony"][0]["dominant_pitch_classes"][0]["pitch_class"] in {"C", "G"}
    assert payload["chord_events"][0]["confidence"] > 0.2
    assert payload["tension_peaks"]


def test_symbolic_layer_expands_repetition_register_and_phrase_metrics(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Motif Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_dir = meta_root / "Motif Song"
    song_dir.mkdir(parents=True)
    (song_dir / "sections.json").write_text(json.dumps([{"start": 0.0, "end": 4.0, "label": "Verse"}, {"start": 4.0, "end": 8.0, "label": "Hook"}]), encoding="utf-8")
    reference_dir = song_dir / "reference"
    reference_dir.mkdir()
    (reference_dir / "beats.json").write_text(
        json.dumps(
            [
                {"time": 0.0, "bar": 1, "beat": 1, "type": "downbeat"},
                {"time": 0.5, "bar": 1, "beat": 2, "type": "beat"},
                {"time": 1.0, "bar": 1, "beat": 3, "type": "beat"},
                {"time": 1.5, "bar": 1, "beat": 4, "type": "beat"},
                {"time": 2.0, "bar": 2, "beat": 1, "type": "downbeat"},
                {"time": 2.5, "bar": 2, "beat": 2, "type": "beat"},
                {"time": 3.0, "bar": 2, "beat": 3, "type": "beat"},
                {"time": 3.5, "bar": 2, "beat": 4, "type": "beat"},
                {"time": 4.0, "bar": 3, "beat": 1, "type": "downbeat"},
                {"time": 4.5, "bar": 3, "beat": 2, "type": "beat"},
                {"time": 5.0, "bar": 3, "beat": 3, "type": "beat"},
                {"time": 5.5, "bar": 3, "beat": 4, "type": "beat"},
            ]
        ),
        encoding="utf-8",
    )
    notes = [
        {"start_s": 0.0, "end_s": 0.45, "pitch_midi": 60, "pitch_name": "C4", "confidence": 0.9, "source_part": "harmonic"},
        {"start_s": 0.5, "end_s": 0.95, "pitch_midi": 64, "pitch_name": "E4", "confidence": 0.9, "source_part": "harmonic"},
        {"start_s": 1.0, "end_s": 1.45, "pitch_midi": 67, "pitch_name": "G4", "confidence": 0.9, "source_part": "harmonic"},
        {"start_s": 2.0, "end_s": 2.45, "pitch_midi": 60, "pitch_name": "C4", "confidence": 0.9, "source_part": "harmonic"},
        {"start_s": 2.5, "end_s": 2.95, "pitch_midi": 64, "pitch_name": "E4", "confidence": 0.9, "source_part": "harmonic"},
        {"start_s": 3.0, "end_s": 3.45, "pitch_midi": 67, "pitch_name": "G4", "confidence": 0.9, "source_part": "harmonic"},
        {"start_s": 4.0, "end_s": 4.9, "pitch_midi": 72, "pitch_name": "C5", "confidence": 0.9, "source_part": "harmonic"},
        {"start_s": 5.0, "end_s": 5.9, "pitch_midi": 74, "pitch_name": "D5", "confidence": 0.9, "source_part": "harmonic"},
        {"start_s": 0.0, "end_s": 0.5, "pitch_midi": 36, "pitch_name": "C2", "confidence": 0.8, "source_part": "bass"},
        {"start_s": 1.0, "end_s": 1.5, "pitch_midi": 38, "pitch_name": "D2", "confidence": 0.8, "source_part": "bass"},
        {"start_s": 2.0, "end_s": 2.5, "pitch_midi": 40, "pitch_name": "E2", "confidence": 0.8, "source_part": "bass"},
        {"start_s": 3.0, "end_s": 3.5, "pitch_midi": 41, "pitch_name": "F2", "confidence": 0.8, "source_part": "bass"},
    ]

    payload = build_symbolic_layer(song_path, meta_root, notes=notes, stems_used=["harmonic", "bass"])

    assert payload["symbolic_summary"]["bass_motion"] == "stepwise"
    assert payload["symbolic_summary"]["repetition_level"] in {"medium", "high"}
    assert payload["symbolic_summary"]["repetition_score"] > 0.0
    assert payload["symbolic_summary"]["pitch_range"]["semitones"] >= 30
    assert payload["symbolic_summary"]["register_centroid"]["label"] in {"low", "mid"}
    assert payload["phrase_contours"]
    assert payload["bass_movement_events"]
    assert payload["repeated_motifs"]
    assert payload["section_symbolic"][0]["phrase_count"] >= 1
    assert payload["section_symbolic"][0]["sustain_ratio"] > 0.0


def test_energy_layer_aggregates_essentia_centroid_flux_and_onsets(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Energy Song.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    song_dir = meta_root / "Energy Song"
    song_dir.mkdir(parents=True)
    essentia_dir = song_dir / "essentia"
    essentia_dir.mkdir()
    (song_dir / "sections.json").write_text(json.dumps([{"start": 0.0, "end": 4.0, "label": "Intro"}, {"start": 4.0, "end": 8.0, "label": "Hook"}]), encoding="utf-8")
    (song_dir / "features.json").write_text(
        json.dumps(
            {
                "global": {"duration_s": 8.0, "energy": {"mean": 0.3, "peak": 1.1, "dynamic_range": 0.8, "volatility": 0.2}},
                "sections": [
                    {"name": "Intro", "start_s": 0.0, "energy": {"level": "low", "trend": "swell", "peak": 0.6}, "summary": "Intro holds back."},
                    {"name": "Hook", "start_s": 4.0, "energy": {"level": "high", "trend": "push", "peak": 1.1}, "summary": "Hook hits harder."},
                ],
            }
        ),
        encoding="utf-8",
    )
    (song_dir / "hints.json").write_text(json.dumps([{"name": "Hook", "start_s": 4.0, "end_s": 8.0, "hints": [{"time_s": 6.0, "kind": "rise", "strength": 0.5, "parts": ["drums"]}]}]), encoding="utf-8")
    (essentia_dir / "loudness_envelope.json").write_text(json.dumps({"times": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0], "loudness": [0.1, 0.2, 0.15, 0.3, 0.8, 0.9, 1.0, 0.7], "envelope": []}), encoding="utf-8")
    (essentia_dir / "spectral_centroid.json").write_text(json.dumps({"times": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0], "centroid": [0.08, 0.09, 0.1, 0.11, 0.21, 0.24, 0.25, 0.23]}), encoding="utf-8")
    (essentia_dir / "rhythm.json").write_text(json.dumps({"onsets": {"times": [0.5, 2.0, 4.5, 6.0], "rate": [0.2, 0.4, 0.3, 1.1, 0.5, 1.5, 0.3, 0.2]}, "beat_loudness": {"values": [0.1, 0.2, 0.4, 0.8], "mean": 0.375, "std": 0.274}}), encoding="utf-8")

    payload = build_energy_layer(song_path, meta_root)

    assert payload["loudness_profile"]["percentile_90"] == 0.9
    assert payload["onset_profile"]["onset_count"] == 4
    assert payload["onset_profile"]["flux_peak"] == 1.5
    assert payload["spectral_profile"]["brightness_trend"] == "rising"
    assert "Centroid stays" in payload["spectral_profile"]["centroid_summary"]
    assert "Onset flux is" in payload["spectral_profile"]["flux_summary"]
    assert payload["section_energy"][1]["centroid_mean"] > payload["section_energy"][0]["centroid_mean"]
    assert payload["section_energy"][1]["loudness_peak"] == 1.0