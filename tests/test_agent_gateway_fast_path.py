import importlib.util
from pathlib import Path

import pytest


def _load_gateway_main_module():
    module_path = Path("/home/darkangel/ai-light-show-v2/llm-server/agent-gateway/main.py")
    spec = importlib.util.spec_from_file_location("agent_gateway_main", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
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


@pytest.mark.asyncio
async def test_fast_path_proposes_prism_flash_for_chord_transition(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_chords":
            return {
                "ok": True,
                "data": {
                    "chords": [
                        {"time_s": 0.0, "bar": 0, "beat": 0, "label": "C#"},
                        {"time_s": 0.48, "bar": 1, "beat": 1, "label": "D#"},
                    ]
                },
            }
        if tool_name == "mcp_read_fixtures":
            return {
                "ok": True,
                "data": {
                    "fixtures": [
                        {"id": "mini_beam_prism_l"},
                        {"id": "mini_beam_prism_r"},
                        {"id": "parcan_l"},
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "add a flash effect to the prisms when the song changes from C# to D#"},
    ])

    assert tool_calls == [("mcp_read_chords", {}), ("mcp_read_fixtures", {})]
    assert result == {
        "used_tools": ["mcp_read_chords", "mcp_read_fixtures"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {"time": 0.48, "fixture_id": "mini_beam_prism_l", "effect": "flash", "duration": 0.5, "data": {}},
                    {"time": 0.48, "fixture_id": "mini_beam_prism_r", "effect": "flash", "duration": 0.5, "data": {}},
                ]
            },
            "title": "Confirm cue add",
            "summary": "Add flash to mini_beam_prism_l, mini_beam_prism_r at 0.480s.",
        },
    }