from pathlib import Path
from typing import Dict

import pytest
from fastmcp import Client

from mcp_server import BackendMcpRuntime, create_backend_mcp
from models.song import Song
from store.dmx_canvas import DMXCanvas

TEST_SONG = "Cinderella - Ella Lee"


class FakeSongService:
    def __init__(self, meta_path: Path) -> None:
        self.meta_path = meta_path

    def list_songs(self):
        return [TEST_SONG]

    def load_metadata(self, filename: str) -> Song:
        return Song(song_id=filename, base_dir=str(self.meta_path))


class FakeArtNetService:
    async def set_continuous_send(self, enabled: bool) -> None:
        del enabled

    async def update_universe(self, universe: bytearray) -> None:
        del universe


class FakeFixture:
    def __init__(self, fixture_id: str, absolute_channels: Dict[str, int]) -> None:
        self.id = fixture_id
        self.absolute_channels = absolute_channels


class FakeStateManager:
    def __init__(self, meta_path: Path) -> None:
        self.meta_path = meta_path
        self.current_song = Song(song_id=TEST_SONG, base_dir=str(meta_path))
        self.timecode = 0.464399
        self.fixtures = [FakeFixture("parcan_l", {"red": 1, "green": 2, "blue": 3, "dim": 4})]
        self._cue_entries = [
            {"time": 0.0, "fixture_id": "parcan_l", "effect": "flash", "duration": 0.5, "data": {}},
            {"time": 16.0, "fixture_id": "parcan_r", "effect": "flash", "duration": 0.5, "data": {}},
        ]
        self.canvas = DMXCanvas.allocate(fps=60, total_frames=5)
        for frame_index in range(self.canvas.total_frames):
            universe = bytearray(512)
            universe[0] = min(255, frame_index * 10)
            universe[1] = min(255, frame_index * 20)
            universe[2] = min(255, frame_index * 30)
            universe[3] = 255
            self.canvas.set_frame(frame_index, universe)

    async def load_song(self, song: str) -> None:
        self.current_song = Song(song_id=song, base_dir=str(self.meta_path))

    async def get_output_universe(self) -> bytearray:
        return bytearray(512)

    async def get_timecode(self) -> float:
        return self.timecode

    def get_cue_entries(self):
        return list(self._cue_entries)

    def get_cue_entries_window(self, start_time: float, end_time: float):
        return [entry for entry in self._cue_entries if start_time <= entry["time"] <= end_time]

    async def replace_cue_sheet_entries(self, entries):
        self._cue_entries = list(entries)
        return {"ok": True, "count": len(self._cue_entries), "entries": list(self._cue_entries)}

    async def replace_cue_entries_window(self, start_time: float, end_time: float, entries):
        retained = [entry for entry in self._cue_entries if not (start_time <= entry["time"] <= end_time)]
        self._cue_entries = retained + list(entries)
        self._cue_entries.sort(key=lambda entry: float(entry.get("time", 0.0)))
        return {
            "ok": True,
            "start_time": start_time,
            "end_time": end_time,
            "count": len(self._cue_entries),
            "window_count": len(entries),
            "entries": list(self._cue_entries),
        }

    async def rerender_dmx_canvas(self):
        return {
            "ok": True,
            "song": self.current_song.song_id,
            "fps": self.canvas.fps,
            "total_frames": self.canvas.total_frames,
            "duration_s": round((self.canvas.total_frames - 1) / float(self.canvas.fps), 3),
            "show_name": "show_20260426",
            "dmx_binary_path": f"data/shows/{self.current_song.song_id}.show_20260426.dmx",
            "dmx_log_path": f"backend/cues/{self.current_song.song_id}.dmx.log",
        }

    async def read_fixture_output_window(self, fixture_id: str, start_time: float, end_time: float, max_samples: int = 240):
        del max_samples
        fixture = next((item for item in self.fixtures if item.id == fixture_id), None)
        if fixture is None:
            return {"ok": False, "reason": "fixture_not_found"}
        start_frame = self.canvas.clamp_frame_index(int(start_time * self.canvas.fps))
        end_frame = self.canvas.clamp_frame_index(int(end_time * self.canvas.fps))
        samples = []
        for frame_index in range(start_frame, end_frame + 1):
            frame = self.canvas.frame_view(frame_index)
            samples.append(
                {
                    "frame": frame_index,
                    "time_s": round(frame_index / float(self.canvas.fps), 3),
                    "channels": {name: int(frame[channel - 1]) for name, channel in fixture.absolute_channels.items()},
                }
            )
        return {
            "ok": True,
            "song": self.current_song.song_id,
            "fixture_id": fixture_id,
            "fps": self.canvas.fps,
            "start_time": start_time,
            "end_time": end_time,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "sample_step_frames": 1,
            "absolute_channels": dict(fixture.absolute_channels),
            "samples": samples,
        }

    def get_chasers(self):
        return [{"id": "parcan_left_to_right", "name": "Parcans left to right", "description": "Test chaser", "effects": []}]


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
async def test_render_dmx_canvas_returns_binary_artifact_metadata():
    meta_path = Path(__file__).resolve().parents[1] / "data" / "output"
    song_service = FakeSongService(meta_path)
    state_manager = FakeStateManager(meta_path)
    ws_manager = FakeWsManager(state_manager, song_service)
    runtime = BackendMcpRuntime()
    runtime.attach(ws_manager, song_service)
    mcp = create_backend_mcp(runtime)

    async with Client(mcp) as client:
        rendered = await client.call_tool("render_dmx_canvas", {})

    assert rendered.data["ok"] is True
    assert rendered.data["data"]["song"] == TEST_SONG
    assert rendered.data["data"]["show_name"] == "show_20260426"
    assert rendered.data["data"]["dmx_binary_path"].endswith(f"{TEST_SONG}.show_20260426.dmx")
    assert rendered.data["data"]["dmx_log_path"].endswith(f"{TEST_SONG}.dmx.log")


@pytest.mark.asyncio
async def test_backend_mcp_tools_cover_song_metadata_and_cues():
    meta_path = Path(__file__).resolve().parents[1] / "data" / "output"
    song_service = FakeSongService(meta_path)
    state_manager = FakeStateManager(meta_path)
    ws_manager = FakeWsManager(state_manager, song_service)
    runtime = BackendMcpRuntime()
    runtime.attach(ws_manager, song_service)
    mcp = create_backend_mcp(runtime)

    async with Client(mcp) as client:
        songs = await client.call_tool("songs_list", {})
        assert songs.data["ok"] is True
        assert TEST_SONG in songs.data["data"]["songs"]

        sections = await client.call_tool("metadata_get_sections", {"song": TEST_SONG})
        assert sections.data["ok"] is True
        assert sections.data["data"]["count"] > 0
        first_section = sections.data["data"]["sections"][0]
        assert "start_bar" in first_section
        assert "start_beat" in first_section
        assert first_section["name"] == "Intro"

        verse = await client.call_tool("metadata_find_section", {"song": TEST_SONG, "section_name": "Verse"})
        assert verse.data["ok"] is True
        assert verse.data["data"]["section"]["name"] == "Verse"
        assert verse.data["data"]["section"]["start_s"] > 0.0
        assert isinstance(verse.data["data"]["section"]["start_bar"], int)
        assert isinstance(verse.data["data"]["section"]["start_beat"], int)

        fallback_verse = await client.call_tool("metadata_find_section", {"song": "unique_song_identifier", "section_name": "Verse"})
        assert fallback_verse.data["ok"] is True
        assert fallback_verse.data["data"]["song"] == TEST_SONG
        assert fallback_verse.data["data"]["section"]["name"] == "Verse"

        fuzzy_verse = await client.call_tool("metadata_find_section", {"section_name": "verse start"})
        assert fuzzy_verse.data["ok"] is True
        assert fuzzy_verse.data["data"]["section"]["name"] == "Verse"

        fuzzy_chorus = await client.call_tool("metadata_find_section", {"section_name": "corus"})
        assert fuzzy_chorus.data["ok"] is True
        assert fuzzy_chorus.data["data"]["section"]["name"] == "Chorus"

        chords = await client.call_tool("metadata_get_chords", {"song": TEST_SONG})
        assert chords.data["ok"] is True
        assert chords.data["data"]["count"] > 0

        chord = await client.call_tool("metadata_find_chord", {"chord": "Am"})
        assert chord.data["ok"] is True
        assert chord.data["data"]["chord"]["time_s"] == 0.46
        assert chord.data["data"]["chord"]["bar"] == 1
        assert chord.data["data"]["chord"]["beat"] == 1

        bar_window = await client.call_tool("metadata_get_bar_beats", {"start_bar": 1, "end_bar": 1})
        assert bar_window.data["ok"] is True
        assert bar_window.data["data"]["count"] > 0
        assert all(item["bar"] == 1 for item in bar_window.data["data"]["beats"])

        bar_beat = await client.call_tool("metadata_find_bar_beat", {"bar": 1, "beat": 1})
        assert bar_beat.data["ok"] is True
        assert bar_beat.data["data"]["position"]["time"] == 0.46
        assert bar_beat.data["data"]["position"]["bar"] == 1
        assert bar_beat.data["data"]["position"]["beat"] == 1

        cursor = await client.call_tool("transport_get_cursor", {})
        assert cursor.data["ok"] is True
        assert cursor.data["data"]["time_s"] == 0.464
        assert cursor.data["data"]["bar"] == 1
        assert cursor.data["data"]["beat"] == 1
        assert cursor.data["data"]["beat_time_s"] == 0.46

        state_manager.timecode = 0.0
        cursor_before_intro = await client.call_tool("transport_get_cursor", {})
        assert cursor_before_intro.data["ok"] is True
        assert cursor_before_intro.data["data"]["section_name"] is None
        assert cursor_before_intro.data["data"]["next_section_name"] == "Intro"

        section_analysis = await client.call_tool("metadata_get_section_analysis", {"song": TEST_SONG, "section_name": "Verse"})
        assert section_analysis.data["ok"] is True
        verse_analysis = section_analysis.data["data"]["section"]
        assert verse_analysis["name"] == "Verse"
        assert verse_analysis["events"]
        assert all(event["dominant_part"] == "mix" for event in verse_analysis["events"])

        song_analysis = await client.call_tool("metadata_get_song_analysis", {"song": TEST_SONG})
        assert song_analysis.data["ok"] is True
        analysis_payload = song_analysis.data["data"]["analysis"]
        assert analysis_payload["features_available"] is True
        assert analysis_payload["hints_available"] is True
        verse_from_analysis = next(section for section in analysis_payload["sections"] if section["name"] == "Verse")
        assert verse_from_analysis["events"]

        chasers = await client.call_tool("chasers_list", {})
        assert chasers.data["ok"] is True
        assert chasers.data["data"]["count"] == 1

        effects = await client.call_tool("list_effects", {})
        assert effects.data["ok"] is True
        assert effects.data["data"]["count"] > 0
        flash = effects.data["data"]["effects"]["flash"]
        assert flash["name"] == "Flash"
        assert flash["tags"] == ["spike", "accent", "hard", "short"]
        assert "description" in flash
        assert "schema" in flash

        window = await client.call_tool("cues_get_window", {"start_time": 0.0, "end_time": 8.0})
        assert window.data["ok"] is True
        assert window.data["data"]["count"] == 1

        sheet = await client.call_tool("cues_get_sheet", {})
        assert sheet.data["ok"] is True
        assert sheet.data["data"]["count"] == 2

        replaced = await client.call_tool("cues_replace_sheet", {"entries": [{"time": 4.0, "chaser_id": "demo", "data": {}}]})
        assert replaced.data["ok"] is True
        assert replaced.data["data"]["count"] == 1

        replaced_window = await client.call_tool(
            "cues_replace_window",
            {"start_time": 0.0, "end_time": 8.0, "entries": [{"time": 2.0, "fixture_id": "parcan_l", "effect": "flash", "duration": 0.25, "data": {}}]},
        )
        assert replaced_window.data["ok"] is True
        assert replaced_window.data["data"]["window_count"] == 1

        rendered = await client.call_tool("render_dmx_canvas", {})
        assert rendered.data["ok"] is True
        assert rendered.data["data"]["fps"] == 60
        assert rendered.data["data"]["show_name"] == "show_20260426"
        assert rendered.data["data"]["dmx_binary_path"].endswith(f"{TEST_SONG}.show_20260426.dmx")
        assert rendered.data["data"]["dmx_log_path"].endswith(f"{TEST_SONG}.dmx.log")

        fixture_output = await client.call_tool(
            "read_fixture_output_window",
            {"fixture_id": "parcan_l", "start_time": 0.0, "end_time": 0.05, "max_samples": 10},
        )
        assert fixture_output.data["ok"] is True
        assert fixture_output.data["data"]["fixture_id"] == "parcan_l"
        assert fixture_output.data["data"]["absolute_channels"]["red"] == 1
        assert fixture_output.data["data"]["samples"]
        first_sample = fixture_output.data["data"]["samples"][0]
        assert first_sample["channels"]["dim"] == 255

        loaded = await client.call_tool("songs_load", {"song": TEST_SONG})
        assert loaded.data["ok"] is True
        assert state_manager.current_song.song_id == TEST_SONG
        assert ws_manager.broadcasts >= 2
