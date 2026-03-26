import importlib
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import main as backend_main
from backend.models.cues import CueSheet
from backend.models.song.beats import Beat, Beats
from services.artnet import ArtNetService
from services.assistant.gateway import AssistantGatewayClient
from services.song_service import SongService
from store.state import StateManager


def _fake_song(song_name: str):
    return SimpleNamespace(
        song_id=song_name,
        audio_url=f"/songs/{song_name}.mp3",
        meta=SimpleNamespace(duration=158.53, bpm=135.0),
        beats=Beats(beats=[Beat(time=37.62, beat=1, bar=21), Beat(time=38.06, beat=2, bar=21)]),
        sections=SimpleNamespace(sections=[{"name": "Instrumental", "start_s": 35.82, "end_s": 57.32}, {"name": "Verse", "start_s": 57.32, "end_s": 84.18}, {"name": "Chorus", "start_s": 84.18, "end_s": 100.28}]),
    )


def _read_until(ws, predicate, max_reads: int = 16):
    for _ in range(max_reads):
        message = ws.receive_json()
        if predicate(message):
            return message
    raise AssertionError("did not receive expected websocket message")


def _fresh_backend_main():
    return importlib.reload(backend_main)


def test_llm_prompt_proposal_and_confirm(monkeypatch, tmp_path):
    calls = []
    gateway_calls = []
    fresh_backend_main = _fresh_backend_main()
    monkeypatch.setenv("ASSISTANT_LOG_DIR", str(tmp_path / "assistant-logs"))

    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = _fake_song(song_name)
        self.song_length_seconds = 158.53
        self.timecode = 37.62
        self.is_playing = False
        self.output_universe = bytearray(512)
        self.editor_universe = bytearray(512)
        self.cue_sheet = CueSheet(song_filename=song_name, entries=[])

    async def _fake_clear_cues(self, from_time: float = 0.0, to_time: float | None = None):
        calls.append((from_time, to_time))
        return {"ok": True, "removed": 4, "remaining": 2}

    async def _fake_gateway_stream(self, messages, assistant_id):
        del assistant_id
        gateway_calls.append(messages)
        assert any(message["role"] == "system" and message["content"] == "Current loaded song: Yonaka - Seize the Power" for message in messages)
        yield {"type": "status", "phase": "thinking", "label": "Thinking"}
        yield {"type": "status", "phase": "executing_tool", "label": "Executing metadata_get_sections"}
        yield {
            "type": "proposal",
            "action_id": "action-1",
            "tool_name": "propose_cue_clear_range",
            "arguments": {"start_time": 84.18, "end_time": 100.28},
            "title": "Confirm cue clear",
            "summary": "Remove cue items from 84.180s to 100.280s.",
        }

    monkeypatch.setattr(fresh_backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: ["Yonaka - Seize the Power"])
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(StateManager, "clear_cue_entries", _fake_clear_cues)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(ArtNetService, "update_universe", _noop_async)
    monkeypatch.setattr(ArtNetService, "arm_fixture", _noop_async)
    monkeypatch.setattr(AssistantGatewayClient, "stream", _fake_gateway_stream)

    with TestClient(fresh_backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            _read_until(ws, lambda message: message.get("type") == "snapshot")

            ws.send_json({"type": "intent", "req_id": "llm-1", "name": "llm.send_prompt", "payload": {"prompt": "clear the chorus cue sheet"}})

            status = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_status")
            assert status["data"]["label"] == "Thinking"

            proposal = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_action_proposed")
            assert proposal["data"]["tool_name"] == "propose_cue_clear_range"
            assert proposal["data"]["arguments"] == {"start_time": 84.18, "end_time": 100.28}

            ws.send_json({"type": "intent", "req_id": "llm-2", "name": "llm.confirm_action", "payload": {"request_id": "llm-1", "action_id": "action-1"}})

            applied = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_action_applied")
            assert applied["data"]["tool_name"] == "propose_cue_clear_range"

            delta = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_delta")
            assert delta["data"]["delta"] == "Cleared cue items from 84.180s to 100.280s. Removed 4 entries."

            done = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_done")
            assert done["data"]["done"] is True

    assert calls == [(84.18, 100.28)]
    assert len(gateway_calls) == 1

    log_files = list((tmp_path / "assistant-logs").glob("assistant-interactions-*.jsonl"))
    assert len(log_files) == 1
    records = [json.loads(line) for line in log_files[0].read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(record["event"] == "request_received" and record["prompt"] == "clear the chorus cue sheet" for record in records)
    assert any(record["event"] == "action_proposed" and record["tool_name"] == "propose_cue_clear_range" for record in records)
    assert any(record["event"] == "action_result" and record["tool_name"] == "propose_cue_clear_range" for record in records)


def test_llm_prompt_clear_all_proposal_and_confirm(monkeypatch, tmp_path):
    calls = []
    fresh_backend_main = _fresh_backend_main()
    monkeypatch.setenv("ASSISTANT_LOG_DIR", str(tmp_path / "assistant-logs"))

    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = _fake_song(song_name)
        self.song_length_seconds = 158.53
        self.timecode = 37.62
        self.is_playing = False
        self.output_universe = bytearray(512)
        self.editor_universe = bytearray(512)
        self.cue_sheet = CueSheet(song_filename=song_name, entries=[])

    async def _fake_clear_all_cues(self):
        calls.append("clear_all")
        return {"ok": True, "removed": 6, "remaining": 0}

    async def _fake_gateway_stream(self, messages, assistant_id):
        del assistant_id, messages
        yield {"type": "status", "phase": "thinking", "label": "Thinking"}
        yield {
            "type": "proposal",
            "action_id": "action-clear-all",
            "tool_name": "propose_cue_clear_all",
            "arguments": {},
            "title": "Confirm cue sheet clear",
            "summary": "Remove all cue items from the cue sheet.",
        }

    monkeypatch.setattr(fresh_backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: ["Yonaka - Seize the Power"])
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(StateManager, "clear_all_cue_entries", _fake_clear_all_cues)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(ArtNetService, "update_universe", _noop_async)
    monkeypatch.setattr(ArtNetService, "arm_fixture", _noop_async)
    monkeypatch.setattr(AssistantGatewayClient, "stream", _fake_gateway_stream)

    with TestClient(fresh_backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            _read_until(ws, lambda message: message.get("type") == "snapshot")

            ws.send_json({"type": "intent", "req_id": "llm-1", "name": "llm.send_prompt", "payload": {"prompt": "clear all the cue"}})

            proposal = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_action_proposed")
            assert proposal["data"]["tool_name"] == "propose_cue_clear_all"
            assert proposal["data"]["arguments"] == {}

            ws.send_json({"type": "intent", "req_id": "llm-2", "name": "llm.confirm_action", "payload": {"request_id": "llm-1", "action_id": "action-clear-all"}})

            applied = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_action_applied")
            assert applied["data"]["tool_name"] == "propose_cue_clear_all"

            delta = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_delta")
            assert delta["data"]["delta"] == "Cleared the cue sheet. Removed 6 entries."

            done = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_done")
            assert done["data"]["done"] is True

    assert calls == ["clear_all"]


def test_llm_prompt_includes_recent_chat_history(monkeypatch, tmp_path):
    seen_messages = []
    fresh_backend_main = _fresh_backend_main()
    monkeypatch.setenv("ASSISTANT_LOG_DIR", str(tmp_path / "assistant-logs"))

    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = _fake_song(song_name)
        self.song_length_seconds = 158.53
        self.timecode = 37.62
        self.is_playing = False
        self.output_universe = bytearray(512)
        self.editor_universe = bytearray(512)
        self.cue_sheet = CueSheet(song_filename=song_name, entries=[])

    async def _fake_gateway_stream(self, messages, assistant_id):
        del assistant_id
        seen_messages.append(messages)
        if len(seen_messages) == 1:
            yield {"type": "status", "phase": "calling_model", "label": "Calling local model"}
            yield {"type": "delta", "delta": "The instrumental starts at 35.820 seconds."}
            yield {"type": "done", "finish_reason": "stop"}
            return

        assert any(message["role"] == "user" and message["content"] == "what about the second instrumental part?" for message in messages)
        assert any(message["role"] == "assistant" and message["content"] == "The instrumental starts at 35.820 seconds." for message in messages)
        yield {"type": "status", "phase": "calling_model", "label": "Calling local model"}
        yield {"type": "delta", "delta": "Repeating the previous command result."}
        yield {"type": "done", "finish_reason": "stop"}

    monkeypatch.setattr(fresh_backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: ["Yonaka - Seize the Power"])
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(ArtNetService, "update_universe", _noop_async)
    monkeypatch.setattr(ArtNetService, "arm_fixture", _noop_async)
    monkeypatch.setattr(AssistantGatewayClient, "stream", _fake_gateway_stream)

    with TestClient(fresh_backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            _read_until(ws, lambda message: message.get("type") == "snapshot")

            ws.send_json({"type": "intent", "req_id": "llm-1", "name": "llm.send_prompt", "payload": {"prompt": "what about the second instrumental part?"}})
            first_done = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_done")
            assert first_done["data"]["done"] is True

            ws.send_json({"type": "intent", "req_id": "llm-2", "name": "llm.send_prompt", "payload": {"prompt": "repeat the last command"}})
            second_done = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_done")
            assert second_done["data"]["done"] is True

    assert len(seen_messages) == 2


def test_llm_confirm_action_is_terminal_for_turn(monkeypatch, tmp_path):
    calls = []
    gateway_calls = 0
    fresh_backend_main = _fresh_backend_main()
    monkeypatch.setenv("ASSISTANT_LOG_DIR", str(tmp_path / "assistant-logs"))

    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = _fake_song(song_name)
        self.song_length_seconds = 158.53
        self.timecode = 37.62
        self.is_playing = False
        self.output_universe = bytearray(512)
        self.editor_universe = bytearray(512)
        self.cue_sheet = CueSheet(song_filename=song_name, entries=[])

    async def _fake_clear_cues(self, from_time: float = 0.0, to_time: float | None = None):
        calls.append((from_time, to_time))
        return {"ok": True, "removed": len(calls), "remaining": max(0, 2 - len(calls))}

    async def _fake_gateway_stream(self, messages, assistant_id):
        del assistant_id
        nonlocal gateway_calls
        gateway_calls += 1
        if gateway_calls > 1:
            raise AssertionError("confirmed actions must not trigger a follow-up gateway request")

        yield {"type": "status", "phase": "thinking", "label": "Thinking"}
        yield {
            "type": "proposal",
            "action_id": "action-1",
            "tool_name": "propose_cue_clear_range",
            "arguments": {"start_time": 84.18, "end_time": 100.28},
            "title": "Confirm chorus clear",
            "summary": "Remove cue items from 84.180s to 100.280s.",
        }

    monkeypatch.setattr(fresh_backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: ["Yonaka - Seize the Power"])
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(StateManager, "clear_cue_entries", _fake_clear_cues)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(ArtNetService, "update_universe", _noop_async)
    monkeypatch.setattr(ArtNetService, "arm_fixture", _noop_async)
    monkeypatch.setattr(AssistantGatewayClient, "stream", _fake_gateway_stream)

    with TestClient(fresh_backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            _read_until(ws, lambda message: message.get("type") == "snapshot")

            ws.send_json({"type": "intent", "req_id": "llm-1", "name": "llm.send_prompt", "payload": {"prompt": "clear the chorus cue sheet"}})

            first_proposal = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_action_proposed")
            assert first_proposal["data"]["action_id"] == "action-1"

            ws.send_json({"type": "intent", "req_id": "llm-2", "name": "llm.confirm_action", "payload": {"request_id": "llm-1", "action_id": "action-1"}})

            first_applied = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_action_applied")
            assert first_applied["data"]["action_id"] == "action-1"

            delta = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_delta")
            assert delta["data"]["delta"] == "Cleared cue items from 84.180s to 100.280s. Removed 1 entries."

            done = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_done")
            assert done["data"]["done"] is True

    assert calls == [(84.18, 100.28)]
    assert gateway_calls == 1


def test_llm_confirm_action_blocks_duplicate_proposal_loop(monkeypatch, tmp_path):
    calls = []
    gateway_calls = 0
    fresh_backend_main = _fresh_backend_main()
    monkeypatch.setenv("ASSISTANT_LOG_DIR", str(tmp_path / "assistant-logs"))

    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = _fake_song(song_name)
        self.song_length_seconds = 158.53
        self.timecode = 37.62
        self.is_playing = False
        self.output_universe = bytearray(512)
        self.editor_universe = bytearray(512)
        self.cue_sheet = CueSheet(song_filename=song_name, entries=[])

    async def _fake_clear_cues(self, from_time: float = 0.0, to_time: float | None = None):
        calls.append((from_time, to_time))
        return {"ok": True, "removed": 0, "remaining": 399}

    async def _fake_gateway_stream(self, messages, assistant_id):
        del assistant_id, messages
        nonlocal gateway_calls
        gateway_calls += 1
        if gateway_calls > 1:
            yield {"type": "status", "phase": "awaiting_tool_calls", "label": "Resolving tool calls"}
            yield {
                "type": "proposal",
                "action_id": "proposal-889719",
                "tool_name": "propose_cue_clear_range",
                "arguments": {"start_time": 84.18, "end_time": 100.28},
                "title": "Confirm cue clear",
                "summary": "Remove cue items from 84.180s to 100.280s.",
            }
            return

        yield {"type": "status", "phase": "thinking", "label": "Thinking"}
        yield {
            "type": "proposal",
            "action_id": "proposal-889719",
            "tool_name": "propose_cue_clear_range",
            "arguments": {"start_time": 84.18, "end_time": 100.28},
            "title": "Confirm cue clear",
            "summary": "Remove cue items from 84.180s to 100.280s.",
        }

    monkeypatch.setattr(fresh_backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: ["Yonaka - Seize the Power"])
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(StateManager, "clear_cue_entries", _fake_clear_cues)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(ArtNetService, "update_universe", _noop_async)
    monkeypatch.setattr(ArtNetService, "arm_fixture", _noop_async)
    monkeypatch.setattr(AssistantGatewayClient, "stream", _fake_gateway_stream)

    with TestClient(fresh_backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            _read_until(ws, lambda message: message.get("type") == "snapshot")

            ws.send_json({"type": "intent", "req_id": "llm-1", "name": "llm.send_prompt", "payload": {"prompt": "clear the chorus cue sheet"}})

            proposal = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_action_proposed")
            assert proposal["data"]["action_id"] == "proposal-889719"

            ws.send_json({"type": "intent", "req_id": "llm-2", "name": "llm.confirm_action", "payload": {"request_id": "llm-1", "action_id": "proposal-889719"}})

            applied = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_action_applied")
            assert applied["data"]["tool_name"] == "propose_cue_clear_range"

            delta = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_delta")
            assert delta["data"]["delta"] == "Cleared cue items from 84.180s to 100.280s. Removed 0 entries."

            done = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_done")
            assert done["data"]["done"] is True

    assert calls == [(84.18, 100.28)]
    assert gateway_calls == 1


def test_llm_clear_conversation_resets_history(monkeypatch, tmp_path):
    seen_messages = []
    fresh_backend_main = _fresh_backend_main()
    monkeypatch.setenv("ASSISTANT_LOG_DIR", str(tmp_path / "assistant-logs"))

    async def _noop_async(*_args, **_kwargs):
        return None

    async def _fake_load_song(self, song_name: str):
        self.current_song = _fake_song(song_name)
        self.song_length_seconds = 158.53
        self.timecode = 37.62
        self.is_playing = False
        self.output_universe = bytearray(512)
        self.editor_universe = bytearray(512)
        self.cue_sheet = CueSheet(song_filename=song_name, entries=[])

    async def _fake_gateway_stream(self, messages, assistant_id):
        del assistant_id
        seen_messages.append(messages)
        if len(seen_messages) == 1:
            yield {"type": "delta", "delta": "The instrumental starts at 35.820 seconds."}
            yield {"type": "done", "finish_reason": "stop"}
            return
        assert not any(message["role"] == "user" and message["content"] == "what about the second instrumental part?" for message in messages)
        assert not any(message["role"] == "assistant" and message["content"] == "The instrumental starts at 35.820 seconds." for message in messages)
        yield {"type": "delta", "delta": "No previous conversation is available."}
        yield {"type": "done", "finish_reason": "stop"}

    monkeypatch.setattr(fresh_backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: ["Yonaka - Seize the Power"])
    monkeypatch.setattr(StateManager, "load_song", _fake_load_song)
    monkeypatch.setattr(StateManager, "_dump_canvas_debug", lambda self, _song_name: None)
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)
    monkeypatch.setattr(ArtNetService, "update_universe", _noop_async)
    monkeypatch.setattr(ArtNetService, "arm_fixture", _noop_async)
    monkeypatch.setattr(AssistantGatewayClient, "stream", _fake_gateway_stream)

    with TestClient(fresh_backend_main.app) as client:
        with client.websocket_connect("/ws") as ws:
            _read_until(ws, lambda message: message.get("type") == "snapshot")

            ws.send_json({"type": "intent", "req_id": "llm-1", "name": "llm.send_prompt", "payload": {"prompt": "what about the second instrumental part?"}})
            _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_done")

            ws.send_json({"type": "intent", "req_id": "llm-clear", "name": "llm.clear_conversation", "payload": {}})
            cleared = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_conversation_cleared")
            assert cleared["data"]["cleared"] is True

            ws.send_json({"type": "intent", "req_id": "llm-2", "name": "llm.send_prompt", "payload": {"prompt": "repeat the last command"}})
            _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_done")

    assert len(seen_messages) == 2