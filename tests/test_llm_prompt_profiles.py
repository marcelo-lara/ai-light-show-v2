from types import SimpleNamespace

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


def test_chat_request_enables_streaming():
    manager = SimpleNamespace(
        state_manager=SimpleNamespace(
            current_song=SimpleNamespace(
                song_id="Test Song",
                meta=SimpleNamespace(song_name="Test Song", bpm=128.5, duration=150.0, song_key="Am"),
            ),
            fixtures=[
                SimpleNamespace(id="parcan_l", name="ParCan L", type="parcan", effects=["fade_in", "flash"]),
                SimpleNamespace(id="head_el150", name="Head EL-150", type="moving_head", effects=["sweep", "seek"]),
            ],
        )
    )

    payload = build_chat_request(manager, "Add a strobe accent", "local", 0.2)

    assert payload["model"] == "local"
    assert payload["temperature"] == 0.2
    assert payload["stream"] is True
    assert len(payload["messages"]) == 3
    assert "Song name: Test Song" in payload["messages"][1]["content"]
    assert "BPM: 128.5 BPM" in payload["messages"][1]["content"]
    assert "Duration: 150 seconds" in payload["messages"][1]["content"]
    assert "Song key: Am" in payload["messages"][1]["content"]
    assert "Available fixtures in this show config:" in payload["messages"][1]["content"]
    assert "parcan_l: ParCan L [parcan] effects: fade_in, flash" in payload["messages"][1]["content"]
    assert "head_el150: Head EL-150 [moving_head] effects: sweep, seek" in payload["messages"][1]["content"]