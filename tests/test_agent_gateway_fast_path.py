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


@pytest.mark.asyncio
async def test_fast_path_resolves_plain_clear_the_cue_to_clear_all_proposal(monkeypatch):
    gateway_main = _load_gateway_main_module()

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "clear the cue"},
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


def test_gateway_answer_prompts_prefer_bar_beat_before_seconds():
    gateway_main = _load_gateway_main_module()

    chord_messages = gateway_main._build_chord_answer_messages(
        [{"role": "user", "content": "when is the first occurrence of chord F?"}],
        {
            "ok": True,
            "data": {
                "occurrence": 1,
                "chord": {"time_s": 35.82, "bar": 20, "beat": 1, "label": "F"},
            },
        },
    )
    cursor_messages = gateway_main._build_cursor_answer_messages(
        [{"role": "user", "content": "where is the cursor?"}],
        {
            "ok": True,
            "data": {"time_s": 35.82, "bar": 20, "beat": 1, "section_name": "Verse"},
        },
    )
    fixtures_messages = gateway_main._build_fixtures_at_bar_answer_messages(
        [{"role": "user", "content": "what fixtures are active at bar 20.1?"}],
        {
            "ok": True,
            "data": {"position": {"time": 35.82, "bar": 20, "beat": 1}},
        },
        {
            "ok": True,
            "data": {
                "entries": [
                    {"fixture_id": "mini_beam_prism_l", "effect": "flash", "duration": 0.5},
                ]
            },
        },
    )

    expected_phrase = "When bar and beat facts are available, report time as <bar>.<beat> (<seconds>s), with bar.beat first. "
    assert expected_phrase in chord_messages[0]["content"]
    assert expected_phrase in cursor_messages[0]["content"]
    assert expected_phrase in fixtures_messages[0]["content"]
    assert "Report the exact bar.beat first and the exact seconds in parentheses in one sentence." in chord_messages[0]["content"]
    assert "You must report the exact bar.beat first and the exact seconds in parentheses in one sentence, with no reinterpretation." in cursor_messages[0]["content"]
    assert "Use exactly one sentence in this structure: At <bar>.<beat> (<time_seconds>s), <fixtures> <effect> for <duration_seconds>s." in fixtures_messages[0]["content"]


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


@pytest.mark.asyncio
async def test_fast_path_proposes_left_prism_flash_on_first_beat_of_each_section(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_sections":
            return {
                "ok": True,
                "data": {
                    "sections": [
                        {"name": "Intro", "start_s": 35.82},
                        {"name": "Verse", "start_s": 57.32},
                        {"name": "Chorus", "start_s": 84.18},
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
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "on the first beat of each section flash the left prism"},
    ])

    assert tool_calls == [("mcp_read_sections", {}), ("mcp_read_fixtures", {})]
    assert result == {
        "used_tools": ["mcp_read_sections", "mcp_read_fixtures"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {"time": 35.82, "fixture_id": "mini_beam_prism_l", "effect": "flash", "duration": 0.5, "data": {}},
                    {"time": 57.32, "fixture_id": "mini_beam_prism_l", "effect": "flash", "duration": 0.5, "data": {}},
                    {"time": 84.18, "fixture_id": "mini_beam_prism_l", "effect": "flash", "duration": 0.5, "data": {}},
                ]
            },
            "title": "Confirm cue add",
            "summary": "Add flash to mini_beam_prism_l at 35.820s, 57.320s, 84.180s.",
        },
    }


@pytest.mark.asyncio
async def test_fast_path_proposes_blue_parcans_for_all_matching_chords(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_chords":
            return {
                "ok": True,
                "data": {
                    "chords": [
                        {"time_s": 25.54, "bar": 14, "beat": 3, "label": "C#"},
                        {"time_s": 27.20, "bar": 15, "beat": 1, "label": "F"},
                        {"time_s": 35.82, "bar": 20, "beat": 1, "label": "C#"},
                    ]
                },
            }
        if tool_name == "mcp_read_fixtures":
            return {
                "ok": True,
                "data": {
                    "fixtures": [
                        {"id": "parcan_l"},
                        {"id": "parcan_r"},
                        {"id": "parcan_pl"},
                        {"id": "parcan_pr"},
                        {"id": "mini_beam_prism_l"},
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "set all parcans to blue when the chord is C#"},
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
                    {"time": 25.54, "fixture_id": "parcan_l", "effect": "full", "duration": 0.0, "data": {"red": 0, "green": 0, "blue": 255}},
                    {"time": 25.54, "fixture_id": "parcan_r", "effect": "full", "duration": 0.0, "data": {"red": 0, "green": 0, "blue": 255}},
                    {"time": 25.54, "fixture_id": "parcan_pl", "effect": "full", "duration": 0.0, "data": {"red": 0, "green": 0, "blue": 255}},
                    {"time": 25.54, "fixture_id": "parcan_pr", "effect": "full", "duration": 0.0, "data": {"red": 0, "green": 0, "blue": 255}},
                    {"time": 35.82, "fixture_id": "parcan_l", "effect": "full", "duration": 0.0, "data": {"red": 0, "green": 0, "blue": 255}},
                    {"time": 35.82, "fixture_id": "parcan_r", "effect": "full", "duration": 0.0, "data": {"red": 0, "green": 0, "blue": 255}},
                    {"time": 35.82, "fixture_id": "parcan_pl", "effect": "full", "duration": 0.0, "data": {"red": 0, "green": 0, "blue": 255}},
                    {"time": 35.82, "fixture_id": "parcan_pr", "effect": "full", "duration": 0.0, "data": {"red": 0, "green": 0, "blue": 255}},
                ]
            },
            "title": "Confirm cue add",
            "summary": "Set parcan_l, parcan_r, parcan_pl, parcan_pr to blue at 25.540s, 35.820s.",
        },
    }