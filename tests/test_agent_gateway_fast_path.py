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
async def test_structured_section_interpretation_resolves_second_verse_start():
    gateway_main = _load_gateway_main_module()

    async def _fake_llm_complete(_client, payload):
        assert payload["tools"] == []
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"intent":"section_timing","section_name":"Verse","section_occurrence":2,"boundary":"start"}'
                    }
                }
            ]
        }

    async def _fake_call_mcp(tool_name, args):
        assert tool_name == "mcp_read_sections"
        assert args == {}
        return {
            "ok": True,
            "data": {
                "sections": [
                    {"name": "Verse", "start_s": 12.5, "end_s": 24.0},
                    {"name": "Verse", "start_s": 57.32, "end_s": 84.18},
                ]
            },
        }

    result = await gateway_main.try_section_timing_interpretation(
        [{"role": "user", "content": "when does the second verse start?"}],
        client=None,
        model="local",
        llm_complete=_fake_llm_complete,
        call_mcp_fn=_fake_call_mcp,
    )

    assert result is not None
    assert result["used_tools"] == ["mcp_read_sections"]
    assert result["answer_text"] == "The second verse starts at 57.320 seconds."


@pytest.mark.asyncio
async def test_structured_section_interpretation_resolves_second_verse_end():
    gateway_main = _load_gateway_main_module()

    async def _fake_llm_complete(_client, _payload):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"intent":"section_timing","section_name":"Verse","section_occurrence":2,"boundary":"end"}'
                    }
                }
            ]
        }

    async def _fake_call_mcp(_tool_name, _args):
        return {
            "ok": True,
            "data": {
                "sections": [
                    {"name": "Verse", "start_s": 12.5, "end_s": 24.0},
                    {"name": "Verse", "start_s": 57.32, "end_s": 84.18},
                ]
            },
        }

    result = await gateway_main.try_section_timing_interpretation(
        [{"role": "user", "content": "when does the second verse end?"}],
        client=None,
        model="local",
        llm_complete=_fake_llm_complete,
        call_mcp_fn=_fake_call_mcp,
    )

    assert result is not None
    assert result["answer_text"] == "The second verse ends at 84.180 seconds."


@pytest.mark.asyncio
async def test_structured_section_interpretation_normalizes_ordinal_in_section_name():
    gateway_main = _load_gateway_main_module()

    async def _fake_llm_complete(_client, _payload):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"intent":"section_timing","section_name":"second verse","section_occurrence":1,"boundary":"start"}'
                    }
                }
            ]
        }

    async def _fake_call_mcp(_tool_name, _args):
        return {
            "ok": True,
            "data": {
                "sections": [
                    {"name": "Verse", "start_s": 12.5, "end_s": 24.0},
                    {"name": "Verse", "start_s": 57.32, "end_s": 84.18},
                ]
            },
        }

    result = await gateway_main.try_section_timing_interpretation(
        [{"role": "user", "content": "when does the second verse start?"}],
        client=None,
        model="local",
        llm_complete=_fake_llm_complete,
        call_mcp_fn=_fake_call_mcp,
    )

    assert result is not None
    assert result["answer_text"] == "The second verse starts at 57.320 seconds."


@pytest.mark.asyncio
async def test_structured_section_interpretation_returns_error_for_missing_occurrence():
    gateway_main = _load_gateway_main_module()

    async def _fake_llm_complete(_client, _payload):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"intent":"section_timing","section_name":"Verse","section_occurrence":2,"boundary":"start"}'
                    }
                }
            ]
        }

    async def _fake_call_mcp(_tool_name, _args):
        return {
            "ok": True,
            "data": {
                "sections": [
                    {"name": "Verse", "start_s": 57.32, "end_s": 84.18},
                ]
            },
        }

    result = await gateway_main.try_section_timing_interpretation(
        [{"role": "user", "content": "when does the second verse start?"}],
        client=None,
        model="local",
        llm_complete=_fake_llm_complete,
        call_mcp_fn=_fake_call_mcp,
    )

    assert result is not None
    assert result["used_tools"] == ["mcp_read_sections"]
    assert result["error"] == {
        "code": "section_not_found",
        "detail": "Section 'Verse' occurrence 2 was not found.",
        "retryable": False,
    }


@pytest.mark.asyncio
async def test_structured_section_interpretation_skips_non_section_prompts():
    gateway_main = _load_gateway_main_module()

    async def _unexpected_llm_complete(_client, _payload):
        raise AssertionError("structured extraction should not run")

    async def _unexpected_call_mcp(_tool_name, _args):
        raise AssertionError("section resolution should not run")

    result = await gateway_main.try_section_timing_interpretation(
        [{"role": "user", "content": "what fixtures are active at bar 20.1?"}],
        client=None,
        model="local",
        llm_complete=_unexpected_llm_complete,
        call_mcp_fn=_unexpected_call_mcp,
    )

    assert result is None


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
async def test_fast_path_adds_blue_flash_to_parcan_at_explicit_second(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "parcan_l"}, {"id": "mini_beam_prism_l"}]}}
        if tool_name == "mcp_read_beats":
            return {
                "ok": True,
                "data": {
                    "beats": [
                        {"time": 1.36, "bar": 1, "beat": 1},
                        {"time": 1.8, "bar": 1, "beat": 2},
                        {"time": 2.26, "bar": 1, "beat": 3},
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "blue flash parcan_l at second 1.36"},
    ])

    assert tool_calls == [
        ("mcp_read_fixtures", {}),
        ("mcp_read_beats", {"start_time": 0.36, "end_time": 3.36}),
    ]
    assert result == {
        "used_tools": ["mcp_read_fixtures", "mcp_read_beats"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {
                        "time": 1.36,
                        "fixture_id": "parcan_l",
                        "effect": "flash",
                        "duration": 0.44,
                        "data": {"channels": ["blue"]},
                    },
                ]
            },
            "title": "Confirm cue add",
            "summary": "Add blue flash to parcan_l at 1.360s.",
        },
    }


@pytest.mark.asyncio
async def test_fast_path_adds_blue_flash_to_parcan_for_one_beat(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "parcan_l"}, {"id": "mini_beam_prism_l"}]}}
        if tool_name == "mcp_read_beats":
            return {
                "ok": True,
                "data": {
                    "beats": [
                        {"time": 1.36, "bar": 1, "beat": 1},
                        {"time": 1.8, "bar": 1, "beat": 2},
                        {"time": 2.26, "bar": 1, "beat": 3},
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "blue flash parcan_l at 1.1 for 1 beat"},
    ])

    assert tool_calls == [
        ("mcp_read_fixtures", {}),
        ("mcp_read_beats", {"start_time": 0.1, "end_time": 3.1}),
    ]
    assert result == {
        "used_tools": ["mcp_read_fixtures", "mcp_read_beats"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {
                        "time": 1.1,
                        "fixture_id": "parcan_l",
                        "effect": "flash",
                        "duration": 0.44,
                        "data": {"channels": ["blue"]},
                    },
                ]
            },
            "title": "Confirm cue add",
            "summary": "Add blue flash to parcan_l at 1.100s.",
        },
    }


@pytest.mark.asyncio
async def test_fast_path_lists_prism_effects(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_fixtures":
            return {
                "ok": True,
                "data": {
                    "fixtures": [
                        {"id": "mini_beam_prism_l", "supported_effects": [{"id": "full"}, {"id": "flash"}, {"id": "move_to_poi"}, {"id": "orbit"}, {"id": "sweep"}, {"id": "fade_out"}]},
                        {"id": "mini_beam_prism_r", "supported_effects": [{"id": "full"}, {"id": "flash"}, {"id": "move_to_poi"}, {"id": "orbit"}, {"id": "sweep"}, {"id": "fade_out"}]},
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "what effect could the prism render?"},
    ])

    assert tool_calls == [("mcp_read_fixtures", {})]
    assert result == {
        "used_tools": ["mcp_read_fixtures"],
        "answer_text": "Prism effects: full, flash, move_to_poi, orbit, sweep, fade_out.",
    }


@pytest.mark.asyncio
async def test_fast_path_lists_available_pois(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_pois":
            return {
                "ok": True,
                "data": {"pois": [{"id": "piano"}, {"id": "table"}, {"id": "sofa"}]},
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "list the available pois"},
    ])

    assert tool_calls == [("mcp_read_pois", {})]
    assert result == {
        "used_tools": ["mcp_read_pois"],
        "answer_text": "Available POIs: piano, table, sofa.",
    }


@pytest.mark.asyncio
async def test_fast_path_reports_section_count(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_sections":
            return {"ok": True, "data": {"count": 7, "sections": []}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "how many sections has this song?"},
    ])

    assert tool_calls == [("mcp_read_sections", {})]
    assert result == {
        "used_tools": ["mcp_read_sections"],
        "answer_text": "This song has 7 sections.",
    }


@pytest.mark.asyncio
async def test_fast_path_reports_chords_in_bar(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_chords":
            return {
                "ok": True,
                "data": {
                    "chords": [
                        {"bar": 21, "beat": 1, "time_s": 37.620, "label": "D#"},
                        {"bar": 21, "beat": 3, "time_s": 38.500, "label": "F"},
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "which chords are in bar 21?"},
    ])

    assert tool_calls == [("mcp_read_chords", {"start_bar": 21, "end_bar": 21})]
    assert result == {
        "used_tools": ["mcp_read_chords"],
        "answer_text": "Bar 21 contains: 21.1 (37.620s) D#, 21.3 (38.500s) F.",
    }


@pytest.mark.asyncio
async def test_fast_path_reports_current_section_and_next_beat(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_cursor":
            return {
                "ok": True,
                "data": {"section_name": "Verse", "next_bar": 21, "next_beat": 1, "next_beat_time_s": 37.620},
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "What section am I in right now, and when is the next beat?"},
    ])

    assert tool_calls == [("mcp_read_cursor", {})]
    assert result == {
        "used_tools": ["mcp_read_cursor"],
        "answer_text": "You are in Verse, and the next beat is 21.1 (37.620s).",
    }


@pytest.mark.asyncio
async def test_fast_path_reports_before_next_section_without_zero_bar_beat(monkeypatch):
    gateway_main = _load_gateway_main_module()

    async def _fake_call_mcp(tool_name, args):
        assert tool_name == "mcp_read_cursor"
        assert args == {}
        return {
            "ok": True,
            "data": {
                "time_s": 0.0,
                "bar": 0,
                "beat": 2,
                "next_bar": 0,
                "next_beat": 3,
                "next_beat_time_s": 0.460,
                "section_name": None,
                "next_section_name": "Intro",
            },
        }

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "What section am I in right now, and when is the next beat?"},
    ])

    assert result == {
        "used_tools": ["mcp_read_cursor"],
        "answer_text": "You are before Intro, and the next beat is at 0.460s.",
    }


@pytest.mark.asyncio
async def test_fast_path_reports_first_chord_occurrence_deterministically(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_find_chord":
            return {"ok": True, "data": {"occurrence": 1, "chord": {"label": "F", "bar": 29, "beat": 1, "time_s": 51.94}}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "what is the first occurrence of the chord F?"},
    ])

    assert tool_calls == [("mcp_find_chord", {"chord": "F", "occurrence": 1})]
    assert result == {
        "used_tools": ["mcp_find_chord"],
        "answer_text": "The first occurrence of chord F is at 29.1 (51.940s).",
    }


@pytest.mark.asyncio
async def test_fast_path_reports_cursor_deterministically(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_cursor":
            return {"ok": True, "data": {"bar": 20, "beat": 1, "time_s": 35.82, "section_name": "Instrumental"}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "where is the cursor?"},
    ])

    assert tool_calls == [("mcp_read_cursor", {})]
    assert result == {
        "used_tools": ["mcp_read_cursor"],
        "answer_text": "The cursor is at 20.1 (35.820s) in Instrumental.",
    }


@pytest.mark.asyncio
async def test_fast_path_reports_cursor_before_next_section(monkeypatch):
    gateway_main = _load_gateway_main_module()

    async def _fake_call_mcp(tool_name, args):
        assert tool_name == "mcp_read_cursor"
        assert args == {}
        return {
            "ok": True,
            "data": {"time_s": 0.0, "bar": 0, "beat": 2, "section_name": None, "next_section_name": "Intro"},
        }

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "where is the cursor?"},
    ])

    assert result == {
        "used_tools": ["mcp_read_cursor"],
        "answer_text": "The cursor is at 0.000s before Intro.",
    }


@pytest.mark.asyncio
async def test_fast_path_lists_left_fixtures_deterministically(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "mini_beam_prism_l"}, {"id": "parcan_l"}, {"id": "parcan_pl"}, {"id": "parcan_r"}]}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "what fixtures are on the left?"},
    ])

    assert tool_calls == [("mcp_read_fixtures", {})]
    assert result == {
        "used_tools": ["mcp_read_fixtures"],
        "answer_text": "mini_beam_prism_l, parcan_l, parcan_pl",
    }


@pytest.mark.asyncio
async def test_fast_path_moves_left_prism_at_start_of_chorus(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_sections":
            return {"ok": True, "data": {"sections": [{"name": "Chorus", "start_s": 84.18, "end_s": 100.28}]}}
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "mini_beam_prism_l"}, {"id": "mini_beam_prism_r"}]}}
        if tool_name == "mcp_read_pois":
            return {"ok": True, "data": {"pois": [{"id": "piano", "name": "Piano"}]}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "Aim the left prism at piano at the start of the chorus"},
    ])

    assert tool_calls == [("mcp_read_sections", {}), ("mcp_read_fixtures", {}), ("mcp_read_pois", {})]
    assert result == {
        "used_tools": ["mcp_read_sections", "mcp_read_fixtures", "mcp_read_pois"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {
                        "time": 84.18,
                        "fixture_id": "mini_beam_prism_l",
                        "effect": "move_to_poi",
                        "duration": 0.0,
                        "data": {"target_POI": "piano"},
                    }
                ]
            },
            "title": "Confirm cue add",
            "summary": "Move mini_beam_prism_l to piano at 84.180s.",
        },
    }


@pytest.mark.asyncio
async def test_fast_path_sets_both_prisms_full_on_second_zero(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "mini_beam_prism_l"}, {"id": "mini_beam_prism_r"}]}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "set both prism to full on second 0.0"},
    ])

    assert tool_calls == [("mcp_read_fixtures", {})]
    assert result == {
        "used_tools": ["mcp_read_fixtures"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {"time": 0.0, "fixture_id": "mini_beam_prism_l", "effect": "full", "duration": 0.0, "data": {}},
                    {"time": 0.0, "fixture_id": "mini_beam_prism_r", "effect": "full", "duration": 0.0, "data": {}},
                ]
            },
            "title": "Confirm cue add",
            "summary": "Set mini_beam_prism_l, mini_beam_prism_r to full at 0.000s.",
        },
    }


@pytest.mark.asyncio
async def test_fast_path_adds_sweep_on_first_beat_of_second_instrumental(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_sections":
            return {
                "ok": True,
                "data": {
                    "sections": [
                        {"name": "Instrumental", "start_s": 35.82, "end_s": 49.70},
                        {"name": "Instrumental", "start_s": 50.14, "end_s": 57.32},
                    ]
                },
            }
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "mini_beam_prism_l"}, {"id": "mini_beam_prism_r"}]}}
        if tool_name == "mcp_read_pois":
            return {"ok": True, "data": {"pois": [{"id": "piano", "name": "Piano"}, {"id": "table", "name": "Table"}]}}
        if tool_name == "mcp_read_beats":
            return {"ok": True, "data": {"beats": [{"time": 50.14, "bar": 28, "beat": 1}, {"time": 50.58, "bar": 28, "beat": 2}]}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "on the first beat of the second instrumental section, sweep left prism from piano to table."},
    ])

    assert tool_calls == [
        ("mcp_read_sections", {}),
        ("mcp_read_fixtures", {}),
        ("mcp_read_pois", {}),
        ("mcp_read_beats", {"start_time": 50.14, "end_time": 57.32}),
    ]
    assert result == {
        "used_tools": ["mcp_read_sections", "mcp_read_fixtures", "mcp_read_pois", "mcp_read_beats"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {
                        "time": 50.14,
                        "fixture_id": "mini_beam_prism_l",
                        "effect": "sweep",
                        "duration": 0.44,
                        "data": {"start_POI": "piano", "subject_POI": "table"},
                    }
                ]
            },
            "title": "Confirm cue add",
            "summary": "Add sweep on mini_beam_prism_l from piano through table at 50.140s.",
        },
    }


@pytest.mark.asyncio
async def test_fast_path_reports_loudest_section(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_sections":
            return {
                "ok": True,
                "data": {
                    "sections": [
                        {"name": "Intro", "start_s": 1.36, "end_s": 35.82},
                        {"name": "Chorus", "start_s": 84.18, "end_s": 100.28},
                    ]
                },
            }
        if tool_name == "mcp_read_loudness":
            if args == {"section": "Intro"}:
                return {"ok": True, "data": {"average": 0.12}}
            if args == {"section": "Chorus"}:
                return {"ok": True, "data": {"average": 0.42}}
        raise AssertionError(f"unexpected tool call: {tool_name} {args}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "which is the loudest section?"},
    ])

    assert tool_calls == [
        ("mcp_read_sections", {}),
        ("mcp_read_loudness", {"section": "Intro"}),
        ("mcp_read_loudness", {"section": "Chorus"}),
    ]
    assert result == {
        "used_tools": ["mcp_read_sections", "mcp_read_loudness", "mcp_read_loudness"],
        "answer_text": "The loudest section is Chorus from 84.180s to 100.280s with average loudness 0.420000.",
    }


@pytest.mark.asyncio
async def test_fast_path_sets_both_prisms_to_full_at_explicit_time(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
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
        {"role": "user", "content": "set both prisms to full at 0.00s"},
    ])

    assert tool_calls == [("mcp_read_fixtures", {})]
    assert result == {
        "used_tools": ["mcp_read_fixtures"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {"time": 0.0, "fixture_id": "mini_beam_prism_l", "effect": "full", "duration": 0.0, "data": {}},
                    {"time": 0.0, "fixture_id": "mini_beam_prism_r", "effect": "full", "duration": 0.0, "data": {}},
                ]
            },
            "title": "Confirm cue add",
            "summary": "Set mini_beam_prism_l, mini_beam_prism_r to full at 0.000s.",
        },
    }


@pytest.mark.asyncio
async def test_fast_path_moves_left_prism_to_piano_before_second_instrumental(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_sections":
            return {
                "ok": True,
                "data": {
                    "sections": [
                        {"name": "Intro", "start_s": 1.36},
                        {"name": "Instrumental", "start_s": 35.82},
                        {"name": "Instrumental", "start_s": 50.14},
                        {"name": "Verse", "start_s": 57.32},
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
        if tool_name == "mcp_read_pois":
            return {
                "ok": True,
                "data": {
                    "pois": [
                        {"id": "piano", "name": "Piano"},
                        {"id": "table", "name": "Table"},
                    ]
                },
            }
        if tool_name == "mcp_read_beats":
            return {
                "ok": True,
                "data": {
                    "beats": [
                        {"time": 48.80, "bar": 27, "beat": 3},
                        {"time": 49.692, "bar": 27, "beat": 4},
                        {"time": 50.14, "bar": 28, "beat": 1},
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "move left prism to piano one beat before the second instrumental section."},
    ])

    assert tool_calls == [
        ("mcp_read_sections", {}),
        ("mcp_read_fixtures", {}),
        ("mcp_read_pois", {}),
        ("mcp_read_beats", {"end_time": 50.14}),
    ]
    assert result == {
        "used_tools": ["mcp_read_sections", "mcp_read_fixtures", "mcp_read_pois", "mcp_read_beats"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {
                        "time": 49.692,
                        "fixture_id": "mini_beam_prism_l",
                        "effect": "move_to_poi",
                        "duration": 0.448,
                        "data": {"target_POI": "piano"},
                    },
                ]
            },
            "title": "Confirm cue add",
            "summary": "Move mini_beam_prism_l to piano at 49.692s.",
        },
    }


@pytest.mark.asyncio
async def test_fast_path_adds_orbit_from_table_to_piano_before_second_instrumental(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_sections":
            return {
                "ok": True,
                "data": {
                    "sections": [
                        {"name": "Intro", "start_s": 1.36},
                        {"name": "Instrumental", "start_s": 35.82},
                        {"name": "Instrumental", "start_s": 50.14},
                        {"name": "Verse", "start_s": 57.32},
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
        if tool_name == "mcp_read_pois":
            return {
                "ok": True,
                "data": {
                    "pois": [
                        {"id": "table", "name": "Table"},
                        {"id": "piano", "name": "Piano"},
                    ]
                },
            }
        if tool_name == "mcp_read_beats":
            return {
                "ok": True,
                "data": {
                    "beats": [
                        {"time": 48.80, "bar": 27, "beat": 3},
                        {"time": 49.692, "bar": 27, "beat": 4},
                        {"time": 50.14, "bar": 28, "beat": 1},
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "orbit the left prism from table to piano one beat before the second instrumental section."},
    ])

    assert tool_calls == [
        ("mcp_read_sections", {}),
        ("mcp_read_fixtures", {}),
        ("mcp_read_pois", {}),
        ("mcp_read_beats", {"end_time": 50.14}),
    ]
    assert result == {
        "used_tools": ["mcp_read_sections", "mcp_read_fixtures", "mcp_read_pois", "mcp_read_beats"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {
                        "time": 49.692,
                        "fixture_id": "mini_beam_prism_l",
                        "effect": "orbit",
                        "duration": 0.448,
                        "data": {"start_POI": "table", "subject_POI": "piano"},
                    },
                ]
            },
            "title": "Confirm cue add",
            "summary": "Add orbit on mini_beam_prism_l from table to piano at 49.692s.",
        },
    }


@pytest.mark.asyncio
async def test_fast_path_adds_sweep_from_table_through_piano_before_second_instrumental(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_sections":
            return {
                "ok": True,
                "data": {
                    "sections": [
                        {"name": "Intro", "start_s": 1.36},
                        {"name": "Instrumental", "start_s": 35.82},
                        {"name": "Instrumental", "start_s": 50.14},
                        {"name": "Verse", "start_s": 57.32},
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
        if tool_name == "mcp_read_pois":
            return {
                "ok": True,
                "data": {
                    "pois": [
                        {"id": "table", "name": "Table"},
                        {"id": "piano", "name": "Piano"},
                        {"id": "sofa", "name": "Sofa"},
                    ]
                },
            }
        if tool_name == "mcp_read_beats":
            return {
                "ok": True,
                "data": {
                    "beats": [
                        {"time": 48.80, "bar": 27, "beat": 3},
                        {"time": 49.692, "bar": 27, "beat": 4},
                        {"time": 50.14, "bar": 28, "beat": 1},
                    ]
                },
            }
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "sweep the left prism from table to piano to sofa one beat before the second instrumental section."},
    ])

    assert tool_calls == [
        ("mcp_read_sections", {}),
        ("mcp_read_fixtures", {}),
        ("mcp_read_pois", {}),
        ("mcp_read_beats", {"end_time": 50.14}),
    ]
    assert result == {
        "used_tools": ["mcp_read_sections", "mcp_read_fixtures", "mcp_read_pois", "mcp_read_beats"],
        "proposal": {
            "type": "proposal",
            "action_id": result["proposal"]["action_id"],
            "tool_name": "propose_cue_add_entries",
            "arguments": {
                "entries": [
                    {
                        "time": 49.692,
                        "fixture_id": "mini_beam_prism_l",
                        "effect": "sweep",
                        "duration": 0.448,
                        "data": {"start_POI": "table", "subject_POI": "piano", "end_POI": "sofa"},
                    },
                ]
            },
            "title": "Confirm cue add",
            "summary": "Add sweep on mini_beam_prism_l from table through piano to sofa at 49.692s.",
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


@pytest.mark.asyncio
async def test_fast_path_proposes_blue_protons_for_all_matching_chords(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_chords":
            return {"ok": True, "data": {"chords": [{"time_s": 25.54, "label": "C#"}, {"time_s": 35.82, "label": "C#"}]}}
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "parcan_l"}, {"id": "parcan_pl"}, {"id": "parcan_pr"}]}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "set all protons to blue when the chord is C#"},
    ])

    assert tool_calls == [("mcp_read_chords", {}), ("mcp_read_fixtures", {})]
    assert result["proposal"]["summary"] == "Set parcan_pl, parcan_pr to blue at 25.540s, 35.820s."


@pytest.mark.asyncio
async def test_fast_path_turns_off_protons_for_matching_chords(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_chords":
            return {"ok": True, "data": {"chords": [{"time_s": 51.94, "label": "F"}]}}
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "parcan_pl"}, {"id": "parcan_pr"}, {"id": "mini_beam_prism_l"}]}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "turn off the protons when the chord is F"},
    ])

    assert tool_calls == [("mcp_read_chords", {}), ("mcp_read_fixtures", {})]
    assert result["proposal"]["summary"] == "Turn off parcan_pl, parcan_pr at 51.940s."
    entries = result["proposal"]["arguments"]["entries"]
    assert all(entry["effect"] == "blackout" for entry in entries)


@pytest.mark.asyncio
async def test_fast_path_fades_out_both_prisms_during_none_spans(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_chords":
            return {
                "ok": True,
                "data": {
                    "chords": [
                        {"time_s": 10.0, "label": "F"},
                        {"time_s": 12.0, "label": "N"},
                        {"time_s": 14.5, "label": "N"},
                        {"time_s": 18.0, "label": "C"},
                    ]
                },
            }
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "mini_beam_prism_l"}, {"id": "mini_beam_prism_r"}]}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "when the chords turns to none, fade out both prisms from 1 to 0 until next chord is not none."},
    ])

    assert tool_calls == [("mcp_read_chords", {}), ("mcp_read_fixtures", {})]
    assert result["proposal"]["summary"] == "Add fade_out to mini_beam_prism_l, mini_beam_prism_r at 12.000s."
    entries = result["proposal"]["arguments"]["entries"]
    assert all(entry["effect"] == "fade_out" for entry in entries)


@pytest.mark.asyncio
async def test_fast_path_turns_off_all_fixtures_during_none_spans(monkeypatch):
    gateway_main = _load_gateway_main_module()
    tool_calls = []

    async def _fake_call_mcp(tool_name, args):
        tool_calls.append((tool_name, args))
        if tool_name == "mcp_read_chords":
            return {"ok": True, "data": {"chords": [{"time_s": 0.0, "label": "N"}, {"time_s": 4.0, "label": "C"}]}}
        if tool_name == "mcp_read_fixtures":
            return {"ok": True, "data": {"fixtures": [{"id": "parcan_l"}, {"id": "parcan_r"}, {"id": "mini_beam_prism_l"}]}}
        raise AssertionError(f"unexpected tool call: {tool_name}")

    monkeypatch.setattr(gateway_main, "call_mcp", _fake_call_mcp)

    result = await gateway_main._run_stream_fast_path([
        {"role": "user", "content": "when the chords is none, turn off all the fixtures."},
    ])

    assert tool_calls == [("mcp_read_chords", {}), ("mcp_read_fixtures", {})]
    entries = result["proposal"]["arguments"]["entries"]
    assert any(entry["fixture_id"] == "parcan_l" and entry["effect"] == "blackout" for entry in entries)
    assert any(entry["fixture_id"] == "parcan_r" and entry["effect"] == "blackout" for entry in entries)
    assert any(entry["fixture_id"] == "mini_beam_prism_l" and entry["effect"] == "fade_out" for entry in entries)