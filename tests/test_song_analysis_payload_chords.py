import json
from pathlib import Path

from backend.api.state.song_payload import parse_chords


def test_parse_chords_keeps_n_and_deduplicates_consecutive_labels(tmp_path: Path):
    beats_path = tmp_path / "beats.json"
    beats_path.write_text(json.dumps([
        {"time": 0.0, "bar": 0, "beat": 1, "chord": "N", "type": "downbeat"},
        {"time": 0.5, "bar": 0, "beat": 2, "chord": "N", "type": "beat"},
        {"time": 1.0, "bar": 1, "beat": 1, "chord": "Fm", "type": "downbeat"},
        {"time": 1.5, "bar": 1, "beat": 2, "chord": "Fm", "type": "beat"},
        {"time": 2.0, "bar": 1, "beat": 3, "chord": "C#", "type": "beat"},
    ]))

    parsed = parse_chords(beats_path)

    assert parsed == [
        {"time_s": 0.0, "label": "N", "bar": 0, "beat": 1},
        {"time_s": 1.0, "label": "Fm", "bar": 1, "beat": 1},
        {"time_s": 2.0, "label": "C#", "bar": 1, "beat": 3},
    ]