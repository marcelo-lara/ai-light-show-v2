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
    def __init__(self):
        self.state_manager = _StateManager()
        self.artnet_service = type("ArtNetStub", (), {"set_continuous_send": self._set_continuous_send})()
        self.events = []
        self.ticker_starts = 0
        self.continuous = []

    async def _set_continuous_send(self, enabled: bool):
        self.continuous.append(enabled)

    async def start_playback_ticker(self):
        self.ticker_starts += 1

    async def broadcast_event(self, level: str, message: str, data=None):
        self.events.append((level, message, data))


@pytest.mark.asyncio
async def test_play_starts_without_external_locking():
    manager = _Manager()

    changed = await play(manager, {})

    assert changed is True
    assert manager.state_manager.is_playing is True
    assert manager.ticker_starts == 1
    assert manager.continuous == [True]
    assert manager.events == [(
        "info",
        "transport_trace",
        {"action": "play", "is_playing": True},
    )]