import asyncio

import pytest

from backend.services.analyzer.service import AnalyzerService


class _Client:
    def __init__(self, queued: int = 0, pending: int = 0, running: int = 0):
        self.lock_calls = []
        self.queued = queued
        self.pending = pending
        self.running = running

    async def get_status(self):
        return {"ok": True, "playback_locked": False, "polling": True, "items": [], "summary": {"queued": self.queued, "pending": self.pending, "running": self.running, "complete": 0, "failed": 0}}

    async def set_playback_lock(self, locked: bool):
        self.lock_calls.append(locked)
        return {"ok": True, "playback_locked": locked, "polling": False, "items": [], "summary": {"queued": self.queued, "pending": self.pending, "running": self.running, "complete": 0, "failed": 0}}


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