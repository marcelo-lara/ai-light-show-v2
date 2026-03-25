from pathlib import Path

import pytest
from fastmcp import Client

from mcp_server import BackendMcpRuntime, create_backend_mcp
from models.song import Song


class FakeSongService:
    def __init__(self, meta_path: Path) -> None:
        self.meta_path = meta_path

    def list_songs(self):
        return ["Yonaka - Seize the Power"]

    def load_metadata(self, filename: str) -> Song:
        return Song(song_id=filename, base_dir=str(self.meta_path))


class FakeArtNetService:
    async def set_continuous_send(self, enabled: bool) -> None:
        del enabled

    async def update_universe(self, universe: bytearray) -> None:
        del universe


class FakeStateManager:
    def __init__(self, meta_path: Path) -> None:
        self.meta_path = meta_path
        self.current_song = Song(song_id="Yonaka - Seize the Power", base_dir=str(meta_path))
        self._cue_entries = [
            {"time": 0.0, "fixture_id": "parcan_l", "effect": "flash", "duration": 0.5, "data": {}},
            {"time": 16.0, "fixture_id": "parcan_r", "effect": "flash", "duration": 0.5, "data": {}},
        ]

    async def load_song(self, song: str) -> None:
        self.current_song = Song(song_id=song, base_dir=str(self.meta_path))

    async def get_output_universe(self) -> bytearray:
        return bytearray(512)

    def get_cue_entries(self):
        return list(self._cue_entries)

    def get_cue_entries_window(self, start_time: float, end_time: float):
        return [entry for entry in self._cue_entries if start_time <= entry["time"] <= end_time]

    async def replace_cue_sheet_entries(self, entries):
        self._cue_entries = list(entries)
        return {"ok": True, "count": len(self._cue_entries), "entries": list(self._cue_entries)}


class FakeWsManager:
    def __init__(self, state_manager: FakeStateManager, song_service: FakeSongService) -> None:
        self.state_manager = state_manager
        self.song_service = song_service
        self.artnet_service = FakeArtNetService()
        self.broadcasts = 0

    async def stop_playback_ticker(self) -> None:
        return None

    async def _schedule_broadcast(self) -> None:
        self.broadcasts += 1


@pytest.mark.asyncio
async def test_backend_mcp_tools_cover_song_metadata_and_cues():
    meta_path = Path("/home/darkangel/ai-light-show-v2/analyzer/meta")
    song_service = FakeSongService(meta_path)
    state_manager = FakeStateManager(meta_path)
    ws_manager = FakeWsManager(state_manager, song_service)
    runtime = BackendMcpRuntime()
    runtime.attach(ws_manager, song_service)
    mcp = create_backend_mcp(runtime)

    async with Client(mcp) as client:
        songs = await client.call_tool("songs_list", {})
        assert songs.data["ok"] is True
        assert "Yonaka - Seize the Power" in songs.data["data"]["songs"]

        sections = await client.call_tool("metadata_get_sections", {"song": "Yonaka - Seize the Power"})
        assert sections.data["ok"] is True
        assert sections.data["data"]["count"] > 0

        chords = await client.call_tool("metadata_get_chords", {"song": "Yonaka - Seize the Power"})
        assert chords.data["ok"] is True
        assert chords.data["data"]["count"] > 0

        window = await client.call_tool("cues_get_window", {"start_time": 0.0, "end_time": 8.0})
        assert window.data["ok"] is True
        assert window.data["data"]["count"] == 1

        replaced = await client.call_tool("cues_replace_sheet", {"entries": [{"time": 4.0, "chaser_id": "demo", "data": {}}]})
        assert replaced.data["ok"] is True
        assert replaced.data["data"]["count"] == 1

        loaded = await client.call_tool("songs_load", {"song": "Yonaka - Seize the Power"})
        assert loaded.data["ok"] is True
        assert state_manager.current_song.song_id == "Yonaka - Seize the Power"
        assert ws_manager.broadcasts >= 2