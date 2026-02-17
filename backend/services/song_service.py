from pathlib import Path
from typing import List
import json
from models.song import Song, SongMetadata

class SongService:
    def __init__(self, songs_path: Path, meta_path: Path):
        self.songs_path = songs_path
        self.meta_path = meta_path

    def list_songs(self) -> List[str]:
        songs = []
        for file in self.songs_path.glob("*.mp3"):  # Assuming mp3
            songs.append(file.stem)
        return songs

    def load_metadata(self, filename: str) -> SongMetadata:
        meta_file = self.meta_path / f"{filename}.json"
        if meta_file.exists():
            with open(meta_file, 'r') as f:
                data = json.load(f)
                return SongMetadata(**data)
        else:
            return SongMetadata(filename=filename, parts={}, hints={}, drums={})

    def save_metadata(self, metadata: SongMetadata):
        meta_file = self.meta_path / f"{metadata.filename}.json"
        with open(meta_file, 'w') as f:
            json.dump(metadata.dict(), f, indent=2)