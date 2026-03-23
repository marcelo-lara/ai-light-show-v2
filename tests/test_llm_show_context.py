from types import SimpleNamespace

from api.intents.llm.show_context import (
    build_cue_section_payload,
    build_cue_window_payload,
    build_section_at_time_payload,
)
from models.chasers.models import ChaserDefinition, ChaserEffect
from models.cues.models import CueEntry, CueSheet


def _manager_with_show_data():
    cue_sheet = CueSheet(
        song_filename="demo.wav",
        entries=[
            CueEntry(time=2.0, fixture_id="parcan_l", effect="flash", duration=1.0, data={}),
            CueEntry(time=10.0, chaser_id="verse_chase", data={"repetitions": 1}),
            CueEntry(time=40.0, fixture_id="head_1", effect="sweep", duration=4.0, data={}),
        ],
    )
    chasers = [
        ChaserDefinition(
            id="verse_chase",
            name="Verse Chase",
            description="",
            effects=[
                ChaserEffect(beat=0.0, fixture_id="parcan_r", effect="strobe", duration=1.0, data={}),
                ChaserEffect(beat=1.0, fixture_id="parcan_l", effect="flash", duration=0.5, data={}),
            ],
        )
    ]
    song = SimpleNamespace(
        meta=SimpleNamespace(song_name="Demo", bpm=120.0),
        sections=SimpleNamespace(
            sections=[
                {"name": "Intro", "start_s": 0.0, "end_s": 8.0},
                {"name": "Verse", "start_s": 8.0, "end_s": 20.0},
            ]
        ),
    )
    state_manager = SimpleNamespace(cue_sheet=cue_sheet, chasers=chasers, current_song=song)
    return SimpleNamespace(state_manager=state_manager)


def test_build_section_at_time_payload_returns_matching_section():
    payload = build_section_at_time_payload(_manager_with_show_data(), 9.5)

    assert payload == {"name": "Verse", "start_s": 8.0, "end_s": 20.0}


def test_build_cue_window_payload_expands_chasers_and_summarizes_fixtures_and_effects():
    payload = build_cue_window_payload(_manager_with_show_data(), 0.0, 12.0)

    assert payload["fixtures_used"] == ["parcan_l", "parcan_r"]
    assert payload["effects_used"] == ["flash", "strobe"]
    assert len(payload["raw_entries"]) == 2
    assert len(payload["expanded_entries"]) == 3
    assert any(entry.get("source_chaser") == "verse_chase" for entry in payload["expanded_entries"])


def test_build_cue_section_payload_uses_section_window():
    payload = build_cue_section_payload(_manager_with_show_data(), "Verse")

    assert payload is not None
    assert payload["section"] == {"name": "Verse", "start_s": 8.0, "end_s": 20.0}
    assert payload["fixtures_used"] == ["parcan_l", "parcan_r"]
    assert payload["effects_used"] == ["flash", "strobe"]