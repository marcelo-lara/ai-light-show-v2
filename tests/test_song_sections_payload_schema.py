from types import SimpleNamespace

from backend.api.state.song_payload import build_song_payload
from backend.models.song.beats import Beats, Beat


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
