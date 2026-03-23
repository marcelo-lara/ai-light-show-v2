import asyncio
import json

import pytest
import websockets


PROMPT_CASES = [
    (
        "What fixtures are used in the Verse?",
        "Looking up section cues",
        "Looking up song timing",
        ["parcan_l", "parcan_r"],
    ),
    (
        "What effects will be rendered in the first 30 seconds?",
        "Looking up cue window",
        "Looking up song timing",
        ["flash", "strobe"],
    ),
    (
        "What section is at the cursor (60.000)?",
        "Looking up cursor section",
        "Looking up song timing",
        ["verse"],
    ),
]


async def _receive_snapshot(ws):
    for _ in range(20):
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        if message.get("type") == "snapshot":
            return message
    raise AssertionError("did not receive initial snapshot")


async def _run_prompt(prompt: str) -> tuple[list[str], str]:
    async with websockets.connect("ws://127.0.0.1:5001/ws", max_size=2**20) as ws:
        snapshot = await _receive_snapshot(ws)
        assert snapshot["state"]["song"]["filename"] == "Yonaka - Seize the Power"

        await ws.send(
            json.dumps(
                {
                    "type": "intent",
                    "req_id": f"live-stack:{prompt}",
                    "name": "llm.send_prompt",
                    "payload": {"prompt": prompt},
                }
            )
        )

        statuses: list[str] = []
        chunks: list[str] = []
        for _ in range(240):
            message = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if message.get("type") != "event":
                continue
            if message.get("message") == "llm_status":
                statuses.append(str(message["data"].get("status") or ""))
                continue
            if message.get("message") == "llm_failed":
                raise AssertionError(f"llm_failed: {message['data'].get('error')}")
            if message.get("message") != "llm_stream":
                continue
            chunks.append(str(message["data"].get("chunk") or ""))
            if message["data"].get("done") is True:
                break
        return statuses, "".join(chunks).strip().lower()


@pytest.mark.live_stack
@pytest.mark.parametrize(("prompt", "expected_status", "forbidden_status", "answer_terms"), PROMPT_CASES)
def test_ws_llm_live_stack_uses_section_and_cue_tools(request, prompt, expected_status, forbidden_status, answer_terms):
    selected_markexpr = (request.config.getoption("-m") or "").strip()
    if "live_stack" not in selected_markexpr:
        pytest.skip("opt-in only; run with -m live_stack")

    statuses, answer = asyncio.run(_run_prompt(prompt))

    assert "Looking up song and fixture details" in statuses
    assert expected_status in statuses
    assert forbidden_status not in statuses
    for term in answer_terms:
        assert term in answer, f"missing term {term!r} in answer: {answer!r}"