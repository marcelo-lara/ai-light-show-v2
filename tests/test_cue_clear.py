import json

from backend.models.cues.crud import clear_cue_sheet, cue_file_path


def _write_entries(cues_path, song_filename, entries):
    cue_file = cue_file_path(cues_path, song_filename)
    cue_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cue_file, "w") as f:
        json.dump(entries, f)


def test_clear_cue_sheet_deletes_file_when_no_range(tmp_path):
    song = "clear_all"
    _write_entries(tmp_path, song, [{"time": 0.5, "fixture_id": "f1", "effect": "flash", "duration": 0.5, "data": {}}])

    clear_cue_sheet(tmp_path, song)

    assert not cue_file_path(tmp_path, song).exists()


def test_clear_cue_sheet_time_window(tmp_path):
    song = "clear_window"
    _write_entries(
        tmp_path,
        song,
        [
            {"time": 1.0, "fixture_id": "f1", "effect": "flash", "duration": 0.5, "data": {}},
            {"time": 2.0, "fixture_id": "f1", "effect": "flash", "duration": 0.5, "data": {}},
            {"time": 3.0, "fixture_id": "f1", "effect": "flash", "duration": 0.5, "data": {}},
        ],
    )

    clear_cue_sheet(tmp_path, song, from_time=1.5, to_time=2.5)

    cue_file = cue_file_path(tmp_path, song)
    assert cue_file.exists()
    with open(cue_file, "r") as f:
        entries = json.load(f)
    assert [entry["time"] for entry in entries] == [1.0, 3.0]
