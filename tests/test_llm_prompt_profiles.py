from api.intents.llm.prompt_profiles import build_messages, load_prompt_profile
from api.intents.llm.request_payload import build_chat_request


def test_default_chat_profile_builds_system_and_user_messages():
    profile = load_prompt_profile()

    messages = build_messages(profile, "Plan a downbeat sweep")

    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "system"
    assert messages[2] == {"role": "user", "content": "Plan a downbeat sweep"}


def test_chat_request_enables_streaming():
    payload = build_chat_request("Add a strobe accent", "local", 0.2)

    assert payload["model"] == "local"
    assert payload["temperature"] == 0.2
    assert payload["stream"] is True
    assert len(payload["messages"]) == 3