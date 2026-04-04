from __future__ import annotations

import json
from pathlib import Path

from src.song_features.stem_patterns import build_stem_patterns
from src.tasks.find_stem_patterns import run as run_find_stem_patterns


def _envelope_payload(values: list[float], *, duration: float) -> dict[str, object]:
    times = [round(index * duration / max(len(values) - 1, 1), 3) for index in range(len(values))]
    return {
        "part": "bass",
        "sample_rate": 100,
        "duration": duration,
        "frame_size": 1,
        "hop_size": 1,
        "times": times,
        "loudness": values,
        "envelope": values,
    }


def test_build_stem_patterns_aligns_with_chord_pattern_windows(tmp_path: Path) -> None:
    meta_dir = tmp_path / "Song"
    essentia_dir = meta_dir / "essentia"
    essentia_dir.mkdir(parents=True)
    repeated = [0.0, 0.2, 0.6, 1.0, 0.6, 0.2, 0.0, 0.1, 0.4, 0.8, 0.4, 0.1, 0.0, 0.2, 0.6, 1.0, 0.6, 0.2]
    (essentia_dir / "bass_loudness_envelope.json").write_text(json.dumps(_envelope_payload(repeated, duration=9.0)), encoding="utf-8")
    chord_patterns = {
        "patterns": [
            {
                "id": "pattern_A",
                "label": "A",
                "sequence": "Cm|Fm|Cm|Fm",
                "bar_count": 4,
                "occurrences": [
                    {"start_time": 0.0, "end_time": 4.0, "start_bar": 1, "end_bar": 4},
                    {"start_time": 4.5, "end_time": 8.5, "start_bar": 5, "end_bar": 8},
                ],
            }
        ]
    }

    payload = build_stem_patterns(meta_dir, chord_patterns)

    assert payload is not None
    assert payload["pattern_count"] == 1
    assert payload["settings"]["alignment"] == "chord_patterns"
    assert payload["patterns"][0]["id"] == "pattern_A"
    assert payload["patterns"][0]["parts"]["bass"]["occurrence_count"] == 2
    assert len(payload["patterns"][0]["parts"]["bass"]["loudness_profile"]) == 24


def test_build_stem_patterns_falls_back_to_signal_windows_without_chord_patterns(tmp_path: Path) -> None:
    meta_dir = tmp_path / "Song"
    essentia_dir = meta_dir / "essentia"
    essentia_dir.mkdir(parents=True)
    repeated = [0.0, 0.2, 0.6, 1.0, 0.6, 0.2, 0.0, 0.1, 0.4, 0.8, 0.4, 0.1, 0.0, 0.2, 0.6, 1.0, 0.6, 0.2]
    (essentia_dir / "bass_loudness_envelope.json").write_text(json.dumps(_envelope_payload(repeated, duration=9.0)), encoding="utf-8")

    payload = build_stem_patterns(meta_dir, None)

    assert payload is not None
    assert payload["settings"]["alignment"] == "signal_windows"
    assert payload["patterns"][0]["source"] == "signal_window"
    assert payload["patterns"][0]["part"] == "bass"


def test_find_stem_patterns_task_writes_artifact_and_skips_cleanly(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_dir = tmp_path / "meta" / "Alpha"
    essentia_dir = meta_dir / "essentia"
    essentia_dir.mkdir(parents=True)
    (meta_dir / "chord_patterns.json").write_text(
        json.dumps(
            {
                "patterns": [
                    {
                        "id": "pattern_A",
                        "label": "A",
                        "sequence": "Cm|Fm|Cm|Fm",
                        "bar_count": 4,
                        "occurrences": [
                            {"start_time": 0.0, "end_time": 4.0, "start_bar": 1, "end_bar": 4},
                            {"start_time": 4.5, "end_time": 8.5, "start_bar": 5, "end_bar": 8},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (essentia_dir / "bass_loudness_envelope.json").write_text(json.dumps(_envelope_payload([0.0, 0.1, 0.5, 1.0, 0.5, 0.1, 0.0, 0.1, 0.5, 1.0], duration=8.5)), encoding="utf-8")

    result = run_find_stem_patterns({"song_path": str(song_path), "meta_path": str(tmp_path / "meta")})

    assert result["status"] == "completed"
    assert result["alignment"] == "chord_patterns"
    info = json.loads((meta_dir / "info.json").read_text(encoding="utf-8"))
    assert (meta_dir / "stem_patterns.json").exists()
    assert info["artifacts"]["stem_patterns_file"].endswith("Alpha/stem_patterns.json")

    missing_song = tmp_path / "songs" / "Beta.mp3"
    missing_song.touch()
    missing_dir = tmp_path / "meta" / "Beta" / "essentia"
    missing_dir.mkdir(parents=True)
    (missing_dir / "bass_loudness_envelope.json").write_text(json.dumps(_envelope_payload([0.0, 0.2, 0.7, 1.0, 0.7, 0.2, 0.0, 0.2, 0.7, 1.0], duration=8.5)), encoding="utf-8")
    skipped = run_find_stem_patterns({"song_path": str(missing_song), "meta_path": str(tmp_path / "meta")})

    assert skipped["status"] == "completed"
    assert skipped["alignment"] == "signal_windows"