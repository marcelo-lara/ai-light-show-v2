import asyncio
import importlib

import pytest

from api.intents.llm.actions.cancel import cancel
from api.intents.llm.actions.send_prompt import send_prompt


send_prompt_module = importlib.import_module("api.intents.llm.actions.send_prompt")


class _FakeStateManager:
    def __init__(self, is_playing: bool = False):
        self._is_playing = is_playing

    async def get_is_playing(self) -> bool:
        return self._is_playing


class _FakeManager:
    def __init__(self, is_playing: bool = False, cancel_result: bool = False):
        self.state_manager = _FakeStateManager(is_playing=is_playing)
        self.cancel_result = cancel_result
        self.cancel_called = False
        self.events = []
        self.task = None
        self.request_id = None

    async def broadcast_event(self, level, message, data=None):
        self.events.append((level, message, data))

    async def cancel_llm_task(self) -> bool:
        self.cancel_called = True
        return self.cancel_result

    def track_llm_task(self, task, request_id: str) -> None:
        self.task = task
        self.request_id = request_id


@pytest.mark.asyncio
async def test_send_prompt_requires_prompt():
    manager = _FakeManager()

    ok = await send_prompt(manager, {"prompt": "   "})

    assert ok is False
    assert manager.events == [("error", "prompt_required", None)]


@pytest.mark.asyncio
async def test_send_prompt_rejects_while_show_running():
    manager = _FakeManager(is_playing=True)

    ok = await send_prompt(manager, {"prompt": "hello"})

    assert ok is False
    assert manager.events[-1][1] == "llm_rejected"
    assert manager.task is None


@pytest.mark.asyncio
async def test_send_prompt_tracks_background_task(monkeypatch):
    manager = _FakeManager()

    async def _fake_stream(_manager, _prompt: str):
        await asyncio.sleep(0)

    monkeypatch.setattr(send_prompt_module, "stream_prompt", _fake_stream)

    ok = await send_prompt(manager, {"prompt": "hello"})
    await asyncio.sleep(0)

    assert ok is False
    assert manager.cancel_called is True
    assert manager.task is not None
    assert manager.request_id


@pytest.mark.asyncio
async def test_cancel_broadcasts_cancelled_when_task_was_active():
    manager = _FakeManager(cancel_result=True)

    ok = await cancel(manager, {})

    assert ok is False
    assert manager.events[-1] == ("info", "llm_cancelled", {"domain": "llm"})


@pytest.mark.asyncio
async def test_cancel_ignored_when_no_task_is_active():
    manager = _FakeManager(cancel_result=False)

    ok = await cancel(manager, {})

    assert ok is False
    assert manager.events[-1][1] == "llm_cancel_ignored"