import pytest

from api.intents.transport.actions.jump_to_time import jump_to_time


class StateManagerStub:
    def __init__(self, timecode: float):
        self.timecode = timecode
        self.seek_calls = []

    async def get_timecode(self) -> float:
        return self.timecode

    async def seek_timecode(self, target: float) -> None:
        self.timecode = target
        self.seek_calls.append(target)

    async def get_output_universe(self):
        return bytearray(512)


class ArtNetServiceStub:
    def __init__(self):
        self.updates = 0

    async def update_universe(self, universe) -> None:
        self.updates += 1


class ManagerStub:
    def __init__(self, timecode: float):
        self.state_manager = StateManagerStub(timecode)
        self.artnet_service = ArtNetServiceStub()
        self.events = []

    async def broadcast_event(self, level: str, message: str, data=None):
        self.events.append((level, message, data))


@pytest.mark.asyncio
async def test_jump_to_time_sync_seek_updates_output_without_broadcast_signal():
    manager = ManagerStub(1.0)

    changed = await jump_to_time(manager, {"time_ms": 1500, "sync": True})

    assert changed is False
    assert manager.state_manager.seek_calls == [1.5]
    assert manager.artnet_service.updates == 1
    assert manager.events == []


@pytest.mark.asyncio
async def test_jump_to_time_sync_seek_skips_nearby_noop():
    manager = ManagerStub(1.500)

    changed = await jump_to_time(manager, {"time_ms": 1508, "sync": True})

    assert changed is False
    assert manager.state_manager.seek_calls == []
    assert manager.artnet_service.updates == 0
    assert manager.events == []