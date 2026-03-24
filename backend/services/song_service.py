from pathlib import Path
from typing import List
from models.song import Song


class SongService:
    def __init__(self, songs_path: Path, meta_path: Path):
        self.songs_path = songs_path
        self.meta_path = meta_path

    def list_songs(self) -> List[str]:
        songs = []
        for file in self.songs_path.glob("*.mp3"):
            songs.append(file.stem)
        songs.sort()
        return songs

    def load_metadata(self, filename: str) -> Song:
        return Song(song_id=filename, base_dir=str(self.meta_path))

    def save_metadata(self, song: Song, sections: List[dict]):
        song.update_sections(sections)
