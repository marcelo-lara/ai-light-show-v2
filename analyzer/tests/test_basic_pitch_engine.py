from __future__ import annotations

import sys
from types import ModuleType

from src.engines.basic_pitch import transcribe_notes


def test_transcribe_notes_normalizes_tuple_events(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "example.wav"
    audio_path.touch()

    inference = ModuleType("basic_pitch.inference")

    def fake_predict(_path: str):
        return {}, None, [
            (1.25, 1.75, 60, 0.91, []),
            (2.0, 2.5, 0, 0.2, []),
        ]

    inference.predict = fake_predict
    package = ModuleType("basic_pitch")
    package.inference = inference
    monkeypatch.setitem(sys.modules, "basic_pitch", package)
    monkeypatch.setitem(sys.modules, "basic_pitch.inference", inference)

    notes = transcribe_notes(audio_path)

    assert notes == [
        {
            "start_s": 1.25,
            "end_s": 1.75,
            "pitch_midi": 60,
            "pitch_name": "C4",
            "confidence": 0.91,
            "source_part": "mix",
        }
    ]