import json
from types import SimpleNamespace
from pathlib import Path

from backend.api.state.song_payload import build_song_payload
from backend.models.song.beats import Beats, Beat
from backend.models.song.io import load_sections_data, save_sections_data


def _build_manager_with_sections(sections):
    song = SimpleNamespace(
        song_id="fake-song",
        audio_url="/songs/fake-song.mp3",
        meta=SimpleNamespace(duration=158.06, bpm=120.0),
        beats=Beats(beats=[Beat(time=0.0, beat=1, bar=0), Beat(time=0.5, beat=2, bar=0)]),
        sections=SimpleNamespace(sections=sections),
    )
    state_manager = SimpleNamespace(current_song=song)
    return SimpleNamespace(state_manager=state_manager)


def test_build_song_payload_normalizes_analyzer_sections_shape():
    manager = _build_manager_with_sections(
        [
            {"start": 35.82, "end": 50.14, "label": "Instrumental"},
            {"start": 1.36, "end": 35.82, "label": "Intro"},
        ]
    )

    payload = build_song_payload(manager)

    assert payload is not None
    assert payload["sections"] == [
        {"name": "Intro", "start_s": 1.36, "end_s": 35.82},
        {"name": "Instrumental", "start_s": 35.82, "end_s": 50.14},
    ]
    assert payload["beats"] == [
        {"time": 0.0, "beat": 1, "bar": 0, "bass": None, "chord": None, "type": "downbeat"},
        {"time": 0.5, "beat": 2, "bar": 0, "bass": None, "chord": None, "type": "beat"},
    ]


def test_save_sections_data_writes_plain_list_schema(tmp_path: Path):
    save_sections_data(tmp_path, [{"start": 1.36, "end": 35.82, "label": "Intro"}])

    payload = json.loads((tmp_path / "sections.json").read_text())

    assert payload == [{"start": 1.36, "end": 35.82, "label": "Intro"}]


def test_load_sections_data_keeps_legacy_wrapper_compatible(tmp_path: Path):
    (tmp_path / "sections.json").write_text(json.dumps({"sections": [{"start": 1.36, "end": 35.82, "label": "Intro"}]}))

    sections = load_sections_data(tmp_path)

    assert sections.sections == [{"start": 1.36, "end": 35.82, "label": "Intro"}]
