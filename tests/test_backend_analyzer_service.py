import asyncio

import pytest

from backend.services.analyzer.service import AnalyzerService


class _Client:
    def __init__(self, queued: int = 0, pending: int = 0, running: int = 0):
        self.lock_calls = []
        self.add_calls = []
        self.remove_calls = []
        self.execute_calls = []
        self.queued = queued
        self.pending = pending
        self.running = running

    async def get_status(self):
        return {"ok": True, "playback_locked": False, "polling": True, "items": [], "summary": {"queued": self.queued, "pending": self.pending, "running": self.running, "complete": 0, "failed": 0}}

    async def set_playback_lock(self, locked: bool):
        self.lock_calls.append(locked)
        return {"ok": True, "playback_locked": locked, "polling": False, "items": [], "summary": {"queued": self.queued, "pending": self.pending, "running": self.running, "complete": 0, "failed": 0}}

    async def list_items(self):
        return [
            {"item_id": "queued-1", "status": "queued"},
            {"item_id": "complete-1", "status": "complete"},
            {"item_id": "running-1", "status": "running"},
        ]

    async def add_item(self, task_type, params):
        self.add_calls.append((task_type, params))
        self.queued += 1
        return {"ok": True, "item_id": "item-1"}

    async def remove_item(self, item_id):
        self.remove_calls.append(item_id)
        self.queued = max(0, self.queued - 1)
        return {"ok": True, "item_id": item_id}

    async def execute_item(self, item_id):
        self.execute_calls.append(item_id)
        if self.queued > 0:
            self.queued -= 1
            self.pending += 1
        return {"ok": True, "item": {"item_id": item_id, "status": "pending"}}


class _Manager:
    def __init__(self, playing: bool = False):
        self.active_connections = [object()]
        self.broadcasts = 0
        self.state_manager = type("StateManagerStub", (), {"get_is_playing": self._get_is_playing})()
        self._playing = playing

    async def _get_is_playing(self):
        return self._playing

    async def _schedule_broadcast(self):
        self.broadcasts += 1


@pytest.mark.asyncio
async def test_analyzer_service_stays_idle_until_queue_activity(monkeypatch):
    service = AnalyzerService()
    service._client = _Client()
    service._manager = _Manager()
    monkeypatch.setattr(service, "_poll_loop", lambda: asyncio.sleep(3600))

    await service.start(service._manager)
    assert service.snapshot()["polling"] is False

    service._client.queued = 1
    await service.notify_queue_activity()

    assert service.snapshot()["polling"] is True

    await service.suspend_polling()


@pytest.mark.asyncio
async def test_analyzer_service_unlock_resumes_only_with_active_queue(monkeypatch):
    service = AnalyzerService()
    service._client = _Client(queued=1)
    service._manager = _Manager()
    service._snapshot = {"available": True, "polling": False, "playback_locked": True, "items": [], "summary": {"queued": 1, "pending": 0, "running": 0, "complete": 0, "failed": 0}}
    monkeypatch.setattr(service, "_poll_loop", lambda: asyncio.sleep(3600))

    await service.unlock_after_playback()

    assert service._client.lock_calls == [False]
    assert service.snapshot()["polling"] is True
    assert service._manager.broadcasts >= 1

    await service.suspend_polling()


@pytest.mark.asyncio
async def test_analyzer_service_lock_and_unlock_without_queue_keep_polling_off(monkeypatch):
    service = AnalyzerService()
    service._client = _Client()
    service._manager = _Manager()
    service._snapshot = {"available": True, "polling": False, "playback_locked": True, "items": [], "summary": {"queued": 0, "pending": 0, "running": 0, "complete": 0, "failed": 0}}
    monkeypatch.setattr(service, "_poll_loop", lambda: asyncio.sleep(3600))

    ok, status = await service.lock_for_playback()

    assert ok is True
    assert status["playback_locked"] is True
    assert service._client.lock_calls == [True]
    assert service.snapshot()["polling"] is False

    await service.unlock_after_playback()

    assert service._client.lock_calls == [True, False]
    assert service.snapshot()["polling"] is False
    assert service._manager.broadcasts >= 1


@pytest.mark.asyncio
async def test_analyzer_service_blocks_playback_lock_when_running():
    service = AnalyzerService()
    service._client = _Client(running=1)
    service._manager = _Manager()

    ok, status = await service.lock_for_playback()

    assert ok is False
    assert status["summary"]["running"] == 1
    assert service._client.lock_calls == []


@pytest.mark.asyncio
async def test_analyzer_service_enqueue_resumes_polling(monkeypatch):
    service = AnalyzerService()
    service._client = _Client()
    service._manager = _Manager()
    monkeypatch.setattr(service, "_poll_loop", lambda: asyncio.sleep(3600))

    result = await service.enqueue_item("generate-md", {"song_path": "/tmp/song.mp3"})

    assert result["item_id"] == "item-1"
    assert service._client.add_calls == [("generate-md", {"song_path": "/tmp/song.mp3"})]
    assert service.snapshot()["polling"] is True

    await service.suspend_polling()


@pytest.mark.asyncio
async def test_analyzer_service_execute_all_runs_queued_only(monkeypatch):
    service = AnalyzerService()
    service._client = _Client(queued=1, running=1)
    service._manager = _Manager()
    monkeypatch.setattr(service, "_poll_loop", lambda: asyncio.sleep(3600))

    result = await service.execute_all_queued()

    assert result == {"item_ids": ["queued-1"], "count": 1}
    assert service._client.execute_calls == ["queued-1"]
    assert service.snapshot()["polling"] is True

    await service.suspend_polling()


@pytest.mark.asyncio
async def test_analyzer_service_remove_all_skips_running_items():
    service = AnalyzerService()
    service._client = _Client(queued=1, running=1)
    service._manager = _Manager()

    result = await service.remove_all_items()

    assert result == {"item_ids": ["queued-1", "complete-1"], "count": 2}
    assert service._client.remove_calls == ["queued-1", "complete-1"]