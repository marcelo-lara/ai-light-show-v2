from types import SimpleNamespace

import pytest

from api.intents.llm.prompt_profiles import build_messages, load_prompt_profile
from api.intents.llm.request_payload import build_chat_request


def test_default_chat_profile_builds_system_and_user_messages():
    profile = load_prompt_profile()

    messages = build_messages(profile, "Plan a downbeat sweep", "Current song context:\n- Song name: Test Song")

    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "system"
    assert messages[2] == {"role": "user", "content": "Plan a downbeat sweep"}
    assert "Current song context:" in messages[1]["content"]


@pytest.mark.asyncio
async def test_chat_request_builds_gateway_payload():
    manager = SimpleNamespace(
        state_manager=SimpleNamespace(
            current_song=SimpleNamespace(
                song_id="Test Song",
                meta=SimpleNamespace(song_name="Test Song", bpm=128.5, duration=150.0, song_key="Am"),
                sections=SimpleNamespace(
                    sections=[
                        {"label": "Verse", "start": 10.0, "end": 30.0},
                    ]
                ),
            ),
            get_timecode=lambda: None,
            get_cue_entries=lambda: [{"time": 1.0, "fixture_id": "parcan_l", "effect": "flash", "duration": 0.5, "data": {}}],
            fixtures=[
                SimpleNamespace(id="parcan_l", name="ParCan L", type="parcan", effects=["fade_in", "flash"]),
                SimpleNamespace(id="head_el150", name="Head EL-150", type="moving_head", effects=["sweep", "seek"]),
            ],
        )
    )
    manager.state_manager.get_timecode = _async_return(20.0)
    manager.state_manager.get_is_playing = _async_return(False)

    payload = await build_chat_request(
        manager,
        "Add a strobe accent",
        "local",
        0.2,
        [
            {"role": "user", "content": "Clear the cue sheet of the intro section."},
            {"role": "assistant", "content": "This will remove existing cue rows. Reply yes or no."},
        ],
    )

    assert payload["model"] == "local"
    assert payload["temperature"] == 0.2
    assert payload["stream"] is True
    assert payload["tool_choice"] == "required"
    assert len(payload["messages"]) == 5
    assert "Song name: Test Song" in payload["messages"][1]["content"]
    assert "BPM: 128.5 BPM" in payload["messages"][1]["content"]
    assert "Duration: 150 seconds" in payload["messages"][1]["content"]
    assert "Song key: Am" in payload["messages"][1]["content"]
    assert "Current playback context:" in payload["messages"][1]["content"]
    assert "Current song position: 20 seconds" in payload["messages"][1]["content"]
    assert "Current section: Verse" in payload["messages"][1]["content"]
    assert "Playback state: paused" in payload["messages"][1]["content"]
    assert "Available fixtures in this show config:" in payload["messages"][1]["content"]
    assert "Current cue sheet summary:" in payload["messages"][1]["content"]
    assert "Cue entries: 1" in payload["messages"][1]["content"]
    assert payload["messages"][2] == {"role": "user", "content": "Clear the cue sheet of the intro section."}
    assert payload["messages"][3] == {"role": "assistant", "content": "This will remove existing cue rows. Reply yes or no."}
    assert payload["messages"][4] == {"role": "user", "content": "Add a strobe accent"}
    assert "parcan_l: ParCan L [parcan] effects: fade_in, flash" in payload["messages"][1]["content"]
    assert "head_el150: Head EL-150 [moving_head] effects: seek, sweep" in payload["messages"][1]["content"]


def test_song_context_payload_can_be_built_for_backend_tools():
    from api.intents.llm.song_context import (
        build_fixture_detail_payload,
        build_fixture_inventory_payload,
        build_song_context_payload,
        build_song_sections_payload,
    )
    from api.intents.llm.cue_sheet_context import build_cue_sheet_payload
    from api.intents.llm.intent_catalog import build_intent_catalog_payload
    from api.intents.llm.playback_context import build_playback_position_payload

    manager = SimpleNamespace(
        state_manager=SimpleNamespace(
            current_song=SimpleNamespace(
                song_id="Test Song",
                meta=SimpleNamespace(song_name="Test Song", bpm=128.5, duration=150.0, song_key="Am"),
                sections=SimpleNamespace(
                    sections=[
                        {"label": "Verse", "start": 10.0, "end": 30.0},
                        {"label": "Intro", "start": 1.36, "end": 10.0},
                    ]
                ),
            ),
            get_cue_entries=lambda: [
                {"time": 1.36, "fixture_id": "parcan_l", "effect": "flash", "duration": 0.5, "data": {}},
                {"time": 2.0, "chaser_id": "intro_chase", "data": {"repetitions": 2}},
            ],
            fixtures=[
                SimpleNamespace(
                    id="parcan_l",
                    name="ParCan L",
                    type="parcan",
                    meta_channels={},
                    mappings={},
                ),
            ],
            _fixture_supported_effects=lambda fixture: {"fade_in", "flash"},
            get_timecode=_async_return(20.0),
            get_is_playing=_async_return(False),
        )
    )

    song_payload = build_song_context_payload(manager)
    sections_payload = build_song_sections_payload(manager)
    cue_sheet_payload = build_cue_sheet_payload(manager)
    fixture_inventory = build_fixture_inventory_payload(manager)
    fixture_detail = build_fixture_detail_payload(manager, "parcan_l")
    intent_catalog = build_intent_catalog_payload()
    playback_payload = _run(build_playback_position_payload(manager))

    assert song_payload["song_name"] == "Test Song"
    assert sections_payload["sections"] == [
        {"name": "Intro", "start_s": 1.36, "end_s": 10.0},
        {"name": "Verse", "start_s": 10.0, "end_s": 30.0},
    ]
    assert cue_sheet_payload["entry_count"] == 2
    assert cue_sheet_payload["entries"][0]["index"] == 0
    assert cue_sheet_payload["entries"][1]["index"] == 1
    assert fixture_inventory[0]["supported_effects"] == ["fade_in", "flash"]
    assert fixture_detail is not None
    assert fixture_detail["id"] == "parcan_l"
    assert playback_payload == {
        "time_s": 20.0,
        "time_ms": 20000,
        "section_name": "Verse",
        "playback_state": "paused",
        "answer": "The cursor is at 20 seconds in the Verse section.",
    }
    assert intent_catalog["undocumented_intents"] == []
    assert intent_catalog["extra_documented_intents"] == []
    assert intent_catalog["intent_count"] == 26


def _async_return(value):
    async def _inner():
        return value

    return _inner


def _run(awaitable):
    import asyncio

    return asyncio.run(awaitable)