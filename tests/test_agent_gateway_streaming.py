from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "llm-server" / "agent-gateway" / "main.py"
sys.path.insert(0, str(MODULE_PATH.parent))
try:
    SPEC = importlib.util.spec_from_file_location("agent_gateway_main", MODULE_PATH)
    assert SPEC and SPEC.loader
    agent_gateway_main = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(agent_gateway_main)
finally:
    sys.path.pop(0)


def test_split_stream_content_breaks_direct_answers_into_multiple_chunks():
    chunks = agent_gateway_main.split_stream_content(
        "Use head_el150 for the chorus sweep and keep the answer short.",
        max_chunk_size=18,
    )

    assert len(chunks) > 1
    assert "".join(chunks) == "Use head_el150 for the chorus sweep and keep the answer short."
    assert all(len(chunk) <= 18 for chunk in chunks)


def test_gateway_tools_include_backend_song_sections_and_no_fake_mcp_sections_tool():
    tool_names = [tool["function"]["name"] for tool in agent_gateway_main.TOOLS]
    tool_descriptions = {tool["function"]["name"]: tool["function"]["description"] for tool in agent_gateway_main.TOOLS}

    assert "backend_get_intent_catalog" in tool_names
    assert "backend_get_current_song_position" in tool_names
    assert "backend_get_current_cue_sheet" in tool_names
    assert "backend_add_cue_row" in tool_names
    assert "backend_update_cue_row_by_index" in tool_names
    assert "backend_delete_cue_row_by_index" in tool_names
    assert "backend_clear_cue_range" in tool_names
    assert "backend_apply_cue_helper" in tool_names
    assert "backend_get_song_sections" in tool_names
    assert "backend_get_section_by_name" in tool_names
    assert "backend_get_section_at_time" in tool_names
    assert "backend_get_cue_window" in tool_names
    assert "backend_get_cue_section" in tool_names
    assert "mcp_get_sections" not in tool_names
    assert "explicitly confirms" in tool_descriptions["backend_delete_cue_row_by_index"]
    assert "explicitly confirms" in tool_descriptions["backend_clear_cue_range"]


@pytest.mark.asyncio
async def test_call_backend_maps_section_at_time_to_query_params(monkeypatch):
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, timeout):
            assert timeout == 15.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            requests.append((url, params))
            return FakeResponse()

    monkeypatch.setattr(agent_gateway_main.httpx, "AsyncClient", FakeClient)

    result = await agent_gateway_main.call_backend("backend_get_section_at_time", {"time_s": 60.0})

    assert result == {"ok": True}
    assert requests == [(f"{agent_gateway_main.BACKEND_BASE_URL}/llm/context/sections/at-time", {"time_s": 60.0})]


@pytest.mark.asyncio
async def test_call_backend_maps_intent_catalog_and_current_cue_sheet(monkeypatch):
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, timeout):
            assert timeout == 15.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            requests.append((url, params))
            return FakeResponse()

    monkeypatch.setattr(agent_gateway_main.httpx, "AsyncClient", FakeClient)

    result_catalog = await agent_gateway_main.call_backend("backend_get_intent_catalog", {})
    result_playback = await agent_gateway_main.call_backend("backend_get_current_song_position", {})
    result_cues = await agent_gateway_main.call_backend("backend_get_current_cue_sheet", {})

    assert result_catalog == {"ok": True}
    assert result_playback == {"ok": True}
    assert result_cues == {"ok": True}
    assert requests == [
        (f"{agent_gateway_main.BACKEND_BASE_URL}/llm/context/intents", None),
        (f"{agent_gateway_main.BACKEND_BASE_URL}/llm/context/playback", None),
        (f"{agent_gateway_main.BACKEND_BASE_URL}/llm/context/cues/current", None),
    ]


@pytest.mark.asyncio
async def test_call_backend_maps_cue_mutation_tools_to_post_routes(monkeypatch):
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, timeout):
            assert timeout == 15.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            requests.append(("GET", url, params))
            return FakeResponse()

        async def post(self, url, json=None):
            requests.append(("POST", url, json))
            return FakeResponse()

    monkeypatch.setattr(agent_gateway_main.httpx, "AsyncClient", FakeClient)

    result_add = await agent_gateway_main.call_backend("backend_add_cue_row", {"time": 12.5, "fixture_id": "head_1", "effect": "strobe"})
    result_update = await agent_gateway_main.call_backend("backend_update_cue_row_by_index", {"index": 1, "patch": {"duration": 2.0}})
    result_delete = await agent_gateway_main.call_backend("backend_delete_cue_row_by_index", {"index": 3})
    result_clear = await agent_gateway_main.call_backend("backend_clear_cue_range", {"from_time": 4.0, "to_time": 8.0})
    result_helper = await agent_gateway_main.call_backend("backend_apply_cue_helper", {"helper_id": "downbeats_and_beats"})

    assert result_add == {"ok": True}
    assert result_update == {"ok": True}
    assert result_delete == {"ok": True}
    assert result_clear == {"ok": True}
    assert result_helper == {"ok": True}
    assert requests == [
        ("POST", f"{agent_gateway_main.BACKEND_BASE_URL}/llm/actions/cues/add", {"payload": {"time": 12.5, "fixture_id": "head_1", "effect": "strobe"}}),
        ("POST", f"{agent_gateway_main.BACKEND_BASE_URL}/llm/actions/cues/update", {"payload": {"index": 1, "patch": {"duration": 2.0}}}),
        ("POST", f"{agent_gateway_main.BACKEND_BASE_URL}/llm/actions/cues/delete", {"payload": {"index": 3}}),
        ("POST", f"{agent_gateway_main.BACKEND_BASE_URL}/llm/actions/cues/clear", {"payload": {"from_time": 4.0, "to_time": 8.0}}),
        ("POST", f"{agent_gateway_main.BACKEND_BASE_URL}/llm/actions/cues/apply-helper", {"payload": {"helper_id": "downbeats_and_beats"}}),
    ]


@pytest.mark.asyncio
async def test_call_backend_maps_cue_window_to_query_params(monkeypatch):
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, timeout):
            assert timeout == 15.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            requests.append((url, params))
            return FakeResponse()

    monkeypatch.setattr(agent_gateway_main.httpx, "AsyncClient", FakeClient)

    result = await agent_gateway_main.call_backend(
        "backend_get_cue_window",
        {"start_s": 0.0, "end_s": 30.0},
    )

    assert result == {"ok": True}
    assert requests == [(f"{agent_gateway_main.BACKEND_BASE_URL}/llm/context/cues/window", {"start_s": 0.0, "end_s": 30.0})]


@pytest.mark.asyncio
async def test_call_backend_rejects_missing_args_for_section_and_window_tools():
    section_result = await agent_gateway_main.call_backend("backend_get_section_by_name", {})
    window_result = await agent_gateway_main.call_backend("backend_get_cue_window", {"start_s": 0.0})

    assert section_result["error"] == "BACKEND_TOOL_INVALID_ARGS"
    assert window_result["error"] == "BACKEND_TOOL_INVALID_ARGS"


@pytest.mark.asyncio
async def test_resolve_tool_call_blocks_destructive_tools_without_confirmation(monkeypatch):
    called = []

    async def fake_call_backend(tool_name, args):
        called.append((tool_name, args))
        return {"ok": True}

    monkeypatch.setattr(agent_gateway_main, "call_backend", fake_call_backend)

    result = await agent_gateway_main.resolve_tool_call(
        "backend_clear_cue_range",
        {"from_time": 0.0, "to_time": 14.539},
        "clear the cue sheet of the intro section",
    )

    assert result["error"] == "BACKEND_CONFIRMATION_REQUIRED"
    assert called == []


@pytest.mark.asyncio
async def test_resolve_tool_call_allows_destructive_tools_with_confirmation(monkeypatch):
    called = []

    async def fake_call_backend(tool_name, args):
        called.append((tool_name, args))
        return {"ok": True}

    monkeypatch.setattr(agent_gateway_main, "call_backend", fake_call_backend)

    result = await agent_gateway_main.resolve_tool_call(
        "backend_clear_cue_range",
        {"from_time": 0.0, "to_time": 14.539},
        "yes, clear it",
    )

    assert result == {"ok": True}
    assert called == [("backend_clear_cue_range", {"from_time": 0.0, "to_time": 14.539})]