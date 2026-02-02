import asyncio
from typing import Dict, List, Optional
from pathlib import Path
import json
from urllib.parse import quote
from models.fixture import Fixture
from models.cue import CueSheet, CueEntry
from models.song import Song, SongMetadata

DMX_CHANNELS = 512

class StateManager:
    def __init__(self, backend_path: Path):
        self.backend_path = backend_path
        self.lock = asyncio.Lock()
        self.dmx_universe: List[int] = [0] * DMX_CHANNELS
        self.fixtures: List[Fixture] = []
        self.current_song: Optional[Song] = None
        self.cue_sheet: Optional[CueSheet] = None
        self.timecode: float = 0.0

    async def load_fixtures(self, fixtures_path: Path):
        async with self.lock:
            with open(fixtures_path, 'r') as f:
                data = json.load(f)
                self.fixtures = [Fixture(**fixture) for fixture in data]

    async def load_song(self, song_filename: str):
        async with self.lock:
            songs_path = self.backend_path / "songs"
            cues_path = self.backend_path / "cues"
            metadata_path = self.backend_path / "metadata"
            audio_url = None
            audio_file = songs_path / f"{song_filename}.mp3"
            if audio_file.exists():
                audio_url = f"/songs/{quote(audio_file.name)}"
            # Load metadata
            metadata_file = metadata_path / f"{song_filename}.metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata_data = json.load(f)
                    metadata = SongMetadata(**metadata_data)
            else:
                metadata = SongMetadata(filename=song_filename, parts={}, hints={}, drums={})

            self.current_song = Song(filename=song_filename, metadata=metadata, audioUrl=audio_url)

            # Load cue sheet
            cue_file = cues_path / f"{song_filename}.cue.json"
            if cue_file.exists():
                with open(cue_file, 'r') as f:
                    cue_data = json.load(f)
                    self.cue_sheet = CueSheet(**cue_data)
            else:
                self.cue_sheet = CueSheet(song_filename=song_filename, entries=[])

    async def update_dmx_channel(self, channel: int, value: int):
        async with self.lock:
            if 1 <= channel <= DMX_CHANNELS and 0 <= value <= 255:
                self.dmx_universe[channel - 1] = value

    async def get_dmx_universe(self) -> List[int]:
        async with self.lock:
            return self.dmx_universe.copy()

    async def add_cue_entry(self, timecode: float, name: Optional[str] = None):
        async with self.lock:
            if self.cue_sheet:
                # Capture current fixture values
                values = {}
                for fixture in self.fixtures:
                    fixture_values = {}
                    for channel_name, channel_num in fixture.channels.items():
                        fixture_values[channel_name] = self.dmx_universe[channel_num - 1]
                    values[fixture.id] = fixture_values
                entry = CueEntry(timecode=timecode, name=name, values=values)
                self.cue_sheet.entries.append(entry)
                # Sort by timecode
                self.cue_sheet.entries.sort(key=lambda e: e.timecode)
                # Save to file
                await self.save_cue_sheet()

    async def save_cue_sheet(self):
        if self.cue_sheet:
            cues_path = Path("backend/cues")
            cue_file = cues_path / f"{self.cue_sheet.song_filename}.cue.json"
            with open(cue_file, 'w') as f:
                json.dump(self.cue_sheet.dict(), f, indent=2)

    async def update_timecode(self, timecode: float):
        async with self.lock:
            self.timecode = timecode
            # Apply cues at this timecode
            if self.cue_sheet:
                for entry in self.cue_sheet.entries:
                    if abs(entry.timecode - timecode) < 0.1:  # within 100ms
                        for fixture_id, fixture_values in entry.values.items():
                            fixture = next((f for f in self.fixtures if f.id == fixture_id), None)
                            if fixture:
                                for channel_name, value in fixture_values.items():
                                    if channel_name in fixture.channels:
                                        channel_num = fixture.channels[channel_name]
                                        self.dmx_universe[channel_num - 1] = value