import json
from pathlib import Path
from types import SimpleNamespace

from backend.api.state.song_payload import build_song_analysis_payload, parse_chord_patterns


def test_parse_chord_patterns_sorts_occurrences_and_filters_invalid_rows(tmp_path: Path) -> None:
    patterns_path = tmp_path / "chord_patterns.json"
    patterns_path.write_text(json.dumps({
        "patterns": [
            {
                "id": "pattern_B",
                "label": "B",
                "bar_count": 2,
                "sequence": "C|G",
                "occurrence_count": 99,
                "occurrences": [
                    {"start_bar": 9, "end_bar": 11, "start_s": 12.0, "end_s": 16.0, "mismatch_count": 2, "sequence": "C|G"},
                    {"start_bar": 1, "end_bar": 3, "start_s": 1.0, "end_s": 5.0, "mismatch_count": 0, "sequence": "C|G"},
                ],
            },
            {
                "id": "pattern_A",
                "label": "A",
                "bar_count": 4,
                "sequence": "Fm|Fm|Fm|Fm",
                "occurrences": [
                    {"start_bar": 4, "end_bar": 4, "start_s": 4.0, "end_s": 4.0, "mismatch_count": 0, "sequence": "bad"},
                    {"start_bar": 2, "end_bar": 6, "start_s": 3.0, "end_s": 9.0, "mismatch_count": 1, "sequence": "Fm|Fm|Fm|Fm"},
                ],
            },
        ]
    }))

    parsed = parse_chord_patterns(patterns_path)

    assert [item["id"] for item in parsed] == ["pattern_B", "pattern_A"]
    assert parsed[0]["occurrence_count"] == 2
    assert parsed[0]["occurrences"][0]["start_bar"] == 1
    assert parsed[1]["occurrence_count"] == 1


def test_build_song_analysis_payload_includes_patterns_from_artifact_manifest(tmp_path: Path) -> None:
    meta_root = tmp_path / "output"
    song_dir = meta_root / "Test Song"
    song_dir.mkdir(parents=True)
    data_root = tmp_path
    artifact_dir = data_root / "artifacts" / "Test Song" / "pattern_mining"
    artifact_dir.mkdir(parents=True)
    (song_dir / "info.json").write_text(json.dumps({
        "artifacts": {
            "pattern_mining": "/data/artifacts/Test Song/pattern_mining/chord_patterns.json",
        }
    }))
    (artifact_dir / "chord_patterns.json").write_text(json.dumps({
        "patterns": [
            {
                "id": "pattern_A",
                "label": "A",
                "bar_count": 4,
                "sequence": "Fm|Fm|Fm|Fm",
                "occurrence_count": 2,
                "occurrences": [
                    {"start_bar": 1, "end_bar": 4, "start_s": 0.464399, "end_s": 7.627755, "mismatch_count": 0, "sequence": "Fm|Fm|Fm|Fm"},
                    {"start_bar": 5, "end_bar": 8, "start_s": 7.627755, "end_s": 14.825941, "mismatch_count": 0, "sequence": "Fm|Fm|Fm|Fm"},
                ],
            }
        ]
    }))

    manager = SimpleNamespace(state_manager=SimpleNamespace(meta_path=str(meta_root)))

    payload = build_song_analysis_payload(manager, "Test Song")

    assert payload is not None
    assert payload["patterns"] == [{
        "id": "pattern_A",
        "label": "A",
        "bar_count": 4,
        "sequence": "Fm|Fm|Fm|Fm",
        "occurrence_count": 2,
        "occurrences": [
            {"start_bar": 1, "end_bar": 4, "start_s": 0.464399, "end_s": 7.627755, "mismatch_count": 0, "sequence": "Fm|Fm|Fm|Fm"},
            {"start_bar": 5, "end_bar": 8, "start_s": 7.627755, "end_s": 14.825941, "mismatch_count": 0, "sequence": "Fm|Fm|Fm|Fm"},
        ],
    }]