import pytest

from backend.api.intents.transport.actions.play import play


class _StateManager:
    def __init__(self):
        self.is_playing = False

    async def set_playback_state(self, playing: bool):
        self.is_playing = playing

    async def get_is_playing(self):
        return self.is_playing


class _Manager:
    def __init__(self, lock_result):
        self.analyzer_service = type("AnalyzerStub", (), {"lock_for_playback": self._lock_for_playback})()
        self._lock_result = lock_result
        self.state_manager = _StateManager()
        self.artnet_service = type("ArtNetStub", (), {"set_continuous_send": self._set_continuous_send})()
        self.events = []
        self.ticker_starts = 0
        self.continuous = []

    async def _lock_for_playback(self):
        return self._lock_result

    async def _set_continuous_send(self, enabled: bool):
        self.continuous.append(enabled)

    async def start_playback_ticker(self):
        self.ticker_starts += 1

    async def broadcast_event(self, level: str, message: str, data=None):
        self.events.append((level, message, data))


@pytest.mark.asyncio
async def test_play_is_blocked_when_analyzer_is_running():
    manager = _Manager((False, {"summary": {"running": 1}}))

    changed = await play(manager, {})

    assert changed is False
    assert manager.state_manager.is_playing is False
    assert manager.ticker_starts == 0
    assert manager.continuous == []
    assert manager.events == [(
        "warning",
        "transport_play_blocked",
        {"reason": "analyzer_running", "analyzer": {"summary": {"running": 1}}},
    )]