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