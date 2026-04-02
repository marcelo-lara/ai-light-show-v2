from __future__ import annotations

from src.essentia_analysis.hints import build_loudness_hints


def test_build_loudness_hints_merges_cross_stem_events() -> None:
    payload = build_loudness_hints(
        {
            "mix": {"loudness_envelope": {"times": [0.0, 0.5, 1.0, 1.5, 2.0], "loudness": [0.1, 0.15, 0.9, 0.2, 0.15]}},
            "drums": {"loudness_envelope": {"times": [0.0, 0.5, 1.0, 1.5, 2.0], "loudness": [0.1, 0.1, 1.0, 0.2, 0.1]}},
            "bass": {"loudness_envelope": {"times": [0.0, 0.5, 1.0, 1.5, 2.0], "loudness": [0.2, 0.25, 0.7, 0.65, 0.2]}},
        },
        [{"label": "Verse", "start": 0.0, "end": 2.1}],
    )

    assert len(payload) == 1
    assert payload[0]["name"] == "Verse"
    assert payload[0]["hints"]
    assert any(hint["kind"] == "sudden_spike" for hint in payload[0]["hints"])
    assert any(set(hint["parts"]) >= {"mix", "drums"} for hint in payload[0]["hints"])


def test_build_loudness_hints_adds_section_sustain_and_song_fallback() -> None:
    payload = build_loudness_hints(
        {"mix": {"loudness_envelope": {"times": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5], "loudness": [0.82, 0.84, 0.83, 0.85, 0.84, 0.86]}}},
        [{"name": "Chorus", "start_s": 0.0, "end_s": 2.6}],
    )

    assert payload[0]["name"] == "Chorus"
    assert any(
        hint == {"kind": "sustain", "start_s": 0.0, "end_s": 2.6, "strength": hint["strength"], "dominant_part": "mix", "parts": ["mix"]}
        for hint in payload[0]["hints"]
    )

    fallback = build_loudness_hints(
        {"mix": {"loudness_envelope": {"times": [0.0, 0.5, 1.0], "loudness": [0.1, 0.9, 0.2]}}}
    )

    assert fallback[0]["name"] == "Song"