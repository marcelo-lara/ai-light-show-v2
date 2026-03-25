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


def test_llm_prompt_proposal_and_confirm(monkeypatch, tmp_path):
    calls = []
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
        if str(messages[-1]["content"]).startswith("The confirmed action has been executed."):
            yield {"type": "status", "phase": "calling_model", "label": "Calling local model"}
            yield {"type": "delta", "delta": "Cleared chorus cues from 84.18s to 100.28s."}
            yield {"type": "done", "finish_reason": "stop"}
            return

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

    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
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

    with TestClient(backend_main.app) as client:
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
            assert delta["data"]["delta"] == "Cleared chorus cues from 84.18s to 100.28s."

            done = _read_until(ws, lambda message: message.get("type") == "event" and message.get("message") == "llm_done")
            assert done["data"]["done"] is True

    assert calls == [(84.18, 100.28)]

    log_files = list((tmp_path / "assistant-logs").glob("assistant-interactions-*.jsonl"))
    assert len(log_files) == 1
    records = [json.loads(line) for line in log_files[0].read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(record["event"] == "request_received" and record["prompt"] == "clear the chorus cue sheet" for record in records)
    assert any(record["event"] == "action_proposed" and record["tool_name"] == "propose_cue_clear_range" for record in records)
    assert any(record["event"] == "action_result" and record["tool_name"] == "propose_cue_clear_range" for record in records)