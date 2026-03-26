import importlib.util
from pathlib import Path

import pytest


def _load_gateway_main_module():
    module_path = Path("/home/darkangel/ai-light-show-v2/llm-server/agent-gateway/main.py")
    spec = importlib.util.spec_from_file_location("agent_gateway_main", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_fast_path_resolves_entire_cue_to_clear_all_proposal(monkeypatch):
    gateway_main = _load_gateway_main_module()

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "clear the entire cue"},
    ])

    assert result == {
        "used_tools": [],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_clear_all",
            "arguments": {},
            "title": "Confirm cue sheet clear",
            "summary": "Remove all cue items from the cue sheet.",
        },
    }


def test_gateway_answer_prompts_omit_song_name_unless_requested():
    gateway_main = _load_gateway_main_module()

    section_messages = gateway_main._build_section_answer_messages(
        [{"role": "user", "content": "when does the chorus start?"}],
        {
            "ok": True,
            "data": {
                "song": "Yonaka - Seize the Power",
                "section": {"name": "Chorus", "start_s": 84.18, "end_s": 100.28},
            },
        },
    )
    chord_messages = gateway_main._build_chord_answer_messages(
        [{"role": "user", "content": "when is the first occurrence of chord F?"}],
        {
            "ok": True,
            "data": {
                "song": "Yonaka - Seize the Power",
                "occurrence": 1,
                "chord": {"time_s": 51.94, "bar": 29, "beat": 1, "label": "F"},
            },
        },
    )
    loudness_messages = gateway_main._build_loudness_answer_messages(
        [{"role": "user", "content": "how loud is the first verse?"}],
        {
            "ok": True,
            "data": {
                "song": "Yonaka - Seize the Power",
                "start_time": 57.32,
                "end_time": 84.18,
                "average": 0.42,
                "minimum": 0.1,
                "maximum": 0.8,
            },
        },
    )

    assert "Do not mention the song name unless the original question explicitly asks for it." in section_messages[0]["content"]
    assert "Do not mention the song name unless the original question explicitly asks for it." in chord_messages[0]["content"]
    assert "Do not mention the song name unless the original question explicitly asks for it." in loudness_messages[0]["content"]
    assert "song=" not in section_messages[1]["content"]
    assert "song=" not in chord_messages[1]["content"]
    assert "song=" not in loudness_messages[1]["content"]