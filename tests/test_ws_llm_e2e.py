from types import SimpleNamespace
import importlib.util
import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

import main as backend_main
import api.intents.llm.stream_runner as stream_runner
from backend.models.song.beats import Beats
from services.artnet import ArtNetService
from services.song_service import SongService
from store.state import StateManager


MODULE_PATH = Path(__file__).resolve().parents[1] / "llm-server" / "agent-gateway" / "main.py"
sys.path.insert(0, str(MODULE_PATH.parent))
try:
    SPEC = importlib.util.spec_from_file_location("agent_gateway_main", MODULE_PATH)
    assert SPEC and SPEC.loader
    agent_gateway_main = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(agent_gateway_main)
finally:
    sys.path.pop(0)


SONG_NAME = "Yonaka - Seize the Power"


def _read_until_type(ws, expected_type: str, max_reads: int = 20):
    for _ in range(max_reads):
        msg = ws.receive_json()
        if msg.get("type") == expected_type:
            return msg
    raise AssertionError(f"did not receive message type {expected_type}")


def _read_until_event(ws, expected_message: str, max_reads: int = 20):
    for _ in range(max_reads):
        msg = ws.receive_json()
        if msg.get("type") == "event" and msg.get("message") == expected_message:
            return msg
    raise AssertionError(f"did not receive event {expected_message}")


class _GatewayProxyClient:
    def __init__(self, *args, **kwargs):
        self._response = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, method: str, url: str, json=None):
        request = agent_gateway_main.ChatRequest(**(json or {}))
        return _GatewayProxyStreamResponse(agent_gateway_main.stream_chat_completion(request))


class _GatewayProxyStreamResponse:
    def __init__(self, iterator):
        self._iterator = iterator

    def raise_for_status(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def aiter_lines(self):
        async for chunk in self._iterator:
            text = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
            for line in text.splitlines():
                yield line


class _CaptureGatewayClient:
    last_json = None

    def __init__(self, *args, **kwargs):
        self._response = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, method: str, url: str, json=None):
        _CaptureGatewayClient.last_json = json
        return _CapturedGatewayStreamResponse()


class _CapturedGatewayStreamResponse:
    def raise_for_status(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def aiter_lines(self):
        yield 'data: {"type":"content","content":"Confirmed.","done":false}'
        yield 'data: {"type":"content","content":"","done":true}'


class _FakeLlamaResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeLlamaStreamResponse:
    def __init__(self, content: str):
        self._content = content

    def raise_for_status(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def aiter_lines(self):
        yield "data: " + json.dumps({"choices": [{"delta": {"content": self._content}, "finish_reason": None}]})
        yield "data: [DONE]"


class _FakeLlamaClient:
    def __init__(self, *args, **kwargs):
        self._tool_call_by_prompt = {
            "where is the cursor?": (
                "backend_get_current_song_position",
                {},
                "The cursor is at 60.0 seconds in the Verse section.",
            ),
            "where does the intro ends?": (
                "backend_get_section_by_name",
                {"section_name": "Intro"},
                "The intro ends at 35.82 seconds.",
            ),
            "what fixtures are used in the verse?": (
                "backend_get_cue_section",
                {"section_name": "Verse"},
                "parcan_l and parcan_r are used in the Verse.",
            ),
            "what effects will be rendered in the first 30 seconds?": (
                "backend_get_cue_window",
                {"start_s": 0.0, "end_s": 30.0},
                "flash and strobe will be rendered in the first 30 seconds.",
            ),
            "what section is at the cursor (60.000)?": (
                "backend_get_section_at_time",
                {"time_s": 60.0},
                "The cursor is inside the Verse section.",
            ),
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json=None):
        messages = list((json or {}).get("messages") or [])
        tool_messages = [message for message in messages if message.get("role") == "tool"]
        if tool_messages:
            latest_tool = json.loads(tool_messages[-1]["content"])
            answer_payload = latest_tool.get("data") or latest_tool
            return _FakeLlamaResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": answer_payload["answer"],
                            }
                        }
                    ]
                }
            )

        prompt = next(message["content"] for message in reversed(messages) if message.get("role") == "user").strip().lower()
        tool_name, args, _content = self._tool_call_by_prompt[prompt]
        return _FakeLlamaResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": f"call-{tool_name}",
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": json_dumps(args),
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        )

    def stream(self, method: str, url: str, json=None):
        messages = list((json or {}).get("messages") or [])
        tool_messages = [message for message in messages if message.get("role") == "tool"]
        latest_tool = json.loads(tool_messages[-1]["content"])
        answer_payload = latest_tool.get("data") or latest_tool
        return _FakeLlamaStreamResponse(answer_payload["answer"])


def json_dumps(value):
    return json.dumps(value, separators=(",", ":"))


@pytest.mark.parametrize(
    ("prompt", "expected_tool", "expected_args", "expected_status", "tool_result", "expected_answer"),
    [
        (
            "Where is the cursor?",
            "backend_get_current_song_position",
            {},
            "Looking up current song position",
            {
                "ok": True,
                "data": {
                    "time_s": 60.0,
                    "time_ms": 60000,
                    "section_name": "Verse",
                    "playback_state": "paused",
                    "answer": "The cursor is at 60.0 seconds in the Verse section.",
                },
            },
            "The cursor is at 60.0 seconds in the Verse section.",
        ),
        (
            "where does the intro ends?",
            "backend_get_section_by_name",
            {"section_name": "Intro"},
            "Looking up section timing",
            {
                "ok": True,
                "data": {
                    "name": "Intro",
                    "start_s": 1.36,
                    "end_s": 35.82,
                    "answer": "The intro ends at 35.82 seconds.",
                },
            },
            "The intro ends at 35.82 seconds.",
        ),
        (
            "What fixtures are used in the Verse?",
            "backend_get_cue_section",
            {"section_name": "Verse"},
            "Looking up section cues",
            {
                "ok": True,
                "data": {
                    "section": {"name": "Verse", "start_s": 57.32, "end_s": 84.18},
                    "fixtures_used": ["parcan_l", "parcan_r"],
                    "effects_used": ["flash", "strobe"],
                    "answer": "parcan_l and parcan_r are used in the Verse.",
                },
            },
            "parcan_l and parcan_r are used in the Verse.",
        ),
        (
            "What effects will be rendered in the first 30 seconds?",
            "backend_get_cue_window",
            {"start_s": 0.0, "end_s": 30.0},
            "Looking up cue window",
            {
                "ok": True,
                "data": {
                    "start_s": 0.0,
                    "end_s": 30.0,
                    "fixtures_used": ["parcan_l", "parcan_r"],
                    "effects_used": ["flash", "strobe"],
                    "answer": "flash and strobe will be rendered in the first 30 seconds.",
                },
            },
            "flash and strobe will be rendered in the first 30 seconds.",
        ),
        (
            "What section is at the cursor (60.000)?",
            "backend_get_section_at_time",
            {"time_s": 60.0},
            "Looking up cursor section",
            {
                "ok": True,
                "data": {
                    "name": "Verse",
                    "start_s": 57.32,
                    "end_s": 84.18,
                    "answer": "The cursor is inside the Verse section.",
                },
            },
            "The cursor is inside the Verse section.",
        ),
    ],
)
def test_ws_llm_retrieval_uses_expected_gateway_tool_for_prompt(
    monkeypatch,
    prompt,
    expected_tool,
    expected_args,
    expected_status,
    tool_result,
    expected_answer,
):
    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = SimpleNamespace(
            song_id=song_name,
            audio_url=f"/songs/{song_name}.mp3",
            meta=SimpleNamespace(song_name=song_name, duration=157.0, bpm=133.929, song_key="C#m"),
            beats=Beats(beats=[]),
            sections=SimpleNamespace(sections=[]),
        )
        self.song_length_seconds = 157.0

    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: [SONG_NAME])
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(agent_gateway_main, "ensure_mcp_started", _noop_async)

    selected_tools = []

    async def _fake_resolve_tool_call(tool_name, args, _user_message=""):
        selected_tools.append((tool_name, args))
        return tool_result

    monkeypatch.setattr(agent_gateway_main, "resolve_tool_call", _fake_resolve_tool_call)
    monkeypatch.setattr(agent_gateway_main.httpx, "AsyncClient", _FakeLlamaClient)
    monkeypatch.setattr(stream_runner.httpx, "AsyncClient", _GatewayProxyClient)

    with TestClient(backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            initial = _read_until_type(ws, "snapshot")
            assert initial["state"]["song"]["filename"] == SONG_NAME

            ws.send_json(
                {
                    "type": "intent",
                    "req_id": "e2e-llm-1",
                    "name": "llm.send_prompt",
                    "payload": {"prompt": prompt},
                }
            )

            status_event = _read_until_event(ws, "llm_status")
            assert status_event["data"]["status"] == "Preparing request context"

            status_event = _read_until_event(ws, "llm_status")
            assert status_event["data"]["status"] == expected_status

            stream_event = _read_until_event(ws, "llm_stream")
            assert stream_event["data"]["chunk"] == expected_answer
            assert stream_event["data"]["done"] is False

            stream_event = _read_until_event(ws, "llm_stream")
            assert stream_event["data"]["chunk"] == ""
            assert stream_event["data"]["done"] is True

            assert selected_tools == [(expected_tool, expected_args)]


def test_ws_llm_send_prompt_forwards_prior_chat_history(monkeypatch):
    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = SimpleNamespace(
            song_id=song_name,
            audio_url=f"/songs/{song_name}.mp3",
            meta=SimpleNamespace(song_name=song_name, duration=157.0, bpm=133.929, song_key="C#m"),
            beats=Beats(beats=[]),
            sections=SimpleNamespace(sections=[]),
        )
        self.song_length_seconds = 157.0

    _CaptureGatewayClient.last_json = None

    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: [SONG_NAME])
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(stream_runner.httpx, "AsyncClient", _CaptureGatewayClient)

    with TestClient(backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            initial = _read_until_type(ws, "snapshot")
            assert initial["state"]["song"]["filename"] == SONG_NAME

            ws.send_json(
                {
                    "type": "intent",
                    "req_id": "e2e-llm-history-1",
                    "name": "llm.send_prompt",
                    "payload": {
                        "prompt": "yes, clear it",
                        "history": [
                            {"role": "user", "text": "clear the cue sheet of the intro section"},
                            {"role": "assistant", "text": "This will remove existing cue rows. Reply yes or no."},
                        ],
                    },
                }
            )

            stream_event = _read_until_event(ws, "llm_stream")
            assert stream_event["data"]["chunk"] == "Confirmed."
            assert stream_event["data"]["done"] is False

            stream_event = _read_until_event(ws, "llm_stream")
            assert stream_event["data"]["chunk"] == ""
            assert stream_event["data"]["done"] is True

    assert _CaptureGatewayClient.last_json is not None
    messages = _CaptureGatewayClient.last_json["messages"]
    assert messages[2] == {"role": "user", "content": "clear the cue sheet of the intro section"}
    assert messages[3] == {"role": "assistant", "content": "This will remove existing cue rows. Reply yes or no."}
    assert messages[4] == {"role": "user", "content": "yes, clear it"}