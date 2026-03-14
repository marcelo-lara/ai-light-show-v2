from types import SimpleNamespace

import pytest

from api.intents.transport.actions.jump_to_section import jump_to_section


class StateManagerStub:
    def __init__(self, sections):
        self.current_song = SimpleNamespace(sections=SimpleNamespace(sections=sections))
        self.seek_calls: list[float] = []

    async def seek_timecode(self, timecode: float) -> None:
        self.seek_calls.append(float(timecode))

    async def get_output_universe(self) -> bytearray:
        return bytearray(512)


class ArtNetStub:
    def __init__(self):
        self.universe_updates = 0

    async def update_universe(self, _universe: bytearray) -> None:
        self.universe_updates += 1


class ManagerStub:
    def __init__(self, sections):
        self.state_manager = StateManagerStub(sections)
        self.artnet_service = ArtNetStub()
        self.events: list[tuple[str, str, dict | None]] = []

    async def broadcast_event(self, level: str, message: str, data=None):
        self.events.append((level, message, data))


@pytest.mark.asyncio
async def test_jump_to_section_seeks_sorted_section_start():
    manager = ManagerStub(
        [
            {"name": "Drop", "start_s": 24.2, "end_s": 40.0},
            {"name": "Intro", "start_s": 0.0, "end_s": 12.0},
            {"name": "Verse", "start_s": 12.0, "end_s": 24.2},
        ]
    )

    changed = await jump_to_section(manager, {"section_index": 1})

    assert changed is True
    assert manager.state_manager.seek_calls == [12.0]
    assert manager.artnet_service.universe_updates == 1
    assert manager.events == []


@pytest.mark.asyncio
async def test_jump_to_section_rejects_invalid_index_and_emits_error():
    manager = ManagerStub(
        [
            {"name": "Intro", "start_s": 0.0, "end_s": 12.0},
            {"name": "Verse", "start_s": 12.0, "end_s": 24.2},
        ]
    )

    changed = await jump_to_section(manager, {"section_index": "bad"})

    assert changed is False
    assert manager.state_manager.seek_calls == []
    assert manager.artnet_service.universe_updates == 0
    assert manager.events == [("error", "invalid_section_index", None)]


@pytest.mark.asyncio
async def test_jump_to_section_rejects_out_of_range_index():
    manager = ManagerStub(
        [{"name": "Intro", "start_s": 0.0, "end_s": 12.0}]
    )

    changed = await jump_to_section(manager, {"section_index": 9})

    assert changed is False
    assert manager.state_manager.seek_calls == []
    assert manager.artnet_service.universe_updates == 0
    assert manager.events == [
        ("error", "section_index_out_of_range", {"section_index": 9, "section_count": 1})
    ]


@pytest.mark.asyncio
async def test_jump_to_section_accepts_analyzer_section_shape():
    manager = ManagerStub(
        [
            {"label": "Intro", "start": 1.36, "end": 35.82},
            {"label": "Instrumental", "start": 35.82, "end": 50.14},
            {"label": "Verse", "start": 57.32, "end": 84.18},
        ]
    )

    changed = await jump_to_section(manager, {"section_index": 2})

    assert changed is True
    assert manager.state_manager.seek_calls == [57.32]
    assert manager.artnet_service.universe_updates == 1
    assert manager.events == []