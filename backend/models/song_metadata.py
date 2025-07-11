"""Song metadata models for the AI Light Show system."""

import json
import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple


def ensure_json_serializable(obj):
    """
    Recursively convert numpy types to native Python types for JSON serialization.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: ensure_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(ensure_json_serializable(item) for item in obj)
    else:
        return obj


class Section:
    """Represents a section of a song (verse, chorus, bridge, etc.)."""
    
    def __init__(self, name: str, start: float, end: float, prompt: str):
        self.name = name
        self.start = start
        self.end = end
        self.prompt = prompt
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start": float(self.start),
            "end": float(self.end),
            "prompt": self.prompt,
        }


class Segment:
    """Represents a segment within a song cluster."""
    
    def __init__(self, start: float, end: float, segment_id: str = ''):
        self.segment_id = segment_id
        self.start = start
        self.end = end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": float(self.start),
            "end": float(self.end),
            "cluster": self.segment_id,
        }

    def __str__(self) -> str:
        return f"Segment(start={self.start}, end={self.end}, segment_id={self.segment_id})"

    def __iter__(self):
        return iter((self.start, self.end, self.segment_id))


class Cluster:
    """Represents a cluster of segments in a song."""
    
    def __init__(self, part: str, segments: List[Segment]):
        self.part = part
        self.segments = segments if isinstance(segments, list) else [Segment(*seg) for seg in segments]

    def __iter__(self):
        return iter(self.segments)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "part": self.part,
            "segments": [seg.to_dict() for seg in self.segments]
        }
    
    def __str__(self) -> str:
        return f"Cluster(part={self.part}, segments={self.segments})"


class SongMetadata:
    """Main class for managing song metadata including beats, chords, and arrangement."""

    def __init__(self, song_name: str, songs_folder: Optional[str] = None, ignore_existing: bool = False):
        self._song_name = song_name[:-4] if song_name.endswith(".mp3") else song_name
        self._title = song_name.replace("_", " ")
        self._genre = "unknown"
        self._bpm = 120
        self._beats: List[Dict[str, Any]] = []
        self._chords: List[Dict[str, Any]] = []
        self._patterns: List[Dict[str, Any]] = []
        self._arrangement: List[Section] = []
        self._duration = 0.0
        self._drums: List[Dict[str, Any]] = []
        self._key_moments: List[Dict[str, Any]] = []
        
        if not songs_folder:
            from ..config import SONGS_DIR
            self._songs_folder = str(SONGS_DIR)
        else:
            self._songs_folder = songs_folder

        self._mp3_path = self._find_mp3_path()
        self._hints_folder = os.path.join(self._songs_folder, "hints")

        if not ignore_existing and self.exists():
            self.load()
        else:
            self.initialize_song_metadata()

    @property
    def song_name(self) -> str:
        return self._song_name

    @property
    def songs_folder(self) -> str:
        return self._songs_folder

    @property
    def mp3_path(self) -> str:
        return self._mp3_path or 'PATH_NOT_FOUND'

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value

    @property
    def drums(self) -> List[Dict[str, Any]]:
        return self._drums

    @drums.setter
    def drums(self, value: List[Dict[str, Any]]):
        self._drums = value

    @property
    def genre(self) -> str:
        return self._genre

    @genre.setter
    def genre(self, value: str):
        self._genre = value

    @property
    def patterns(self) -> List[Dict[str, Any]]:
        return self._patterns

    @patterns.setter
    def patterns(self, value: List[Dict[str, Any]]):
        self._patterns = value

    @property
    def duration(self) -> float:
        return self._duration

    @duration.setter
    def duration(self, value: float):
        self._duration = float(value)

    @property
    def bpm(self) -> int:
        return self._bpm

    @bpm.setter
    def bpm(self, value: int):
        self._bpm = value

    @property
    def beats(self) -> List[Dict[str, Any]]:
        return self._beats

    @beats.setter
    def beats(self, value: List[Dict[str, Any]]):
        self._beats = value

    @property
    def chords(self) -> List[Dict[str, Any]]:
        return self._chords

    @chords.setter
    def chords(self, value: List[Dict[str, Any]]):
        self._chords = value

    @property
    def key_moments(self) -> List[Dict[str, Any]]:
        return self._key_moments

    @key_moments.setter
    def key_moments(self, value: List[Dict[str, Any]]):
        self._key_moments = value

    @property
    def arrangement(self) -> List[Section]:
        return self._arrangement

    @property
    def placeholder_prop(self) -> bool:
        """True when the arrangement is a placeholder."""
        if len(self._arrangement) > 0 and isinstance(self._arrangement[0], Section):
            return "(placeholder)" in self._arrangement[0].prompt
        return len(self._arrangement) == 0


    @arrangement.setter
    def arrangement(self, value: List[Section]):
        if not isinstance(value, list):
            raise TypeError("Arrangement must be a list of Section objects.")
        if not all(isinstance(v, Section) for v in value):
            raise TypeError("All elements of arrangement must be Section objects.")
        self._arrangement = value

    def _find_mp3_path(self) -> Optional[str]:
        """Try to locate the MP3 file for this song."""
        song_file = f"{self._song_name}.mp3" if not self._song_name.endswith(".mp3") else self._song_name

        mp3_path = os.path.join(self._songs_folder, song_file)
        if os.path.isfile(mp3_path):
            return mp3_path
        else:
            print(f"⚠️ Warning: MP3 file not found for '{self._song_name}' at {mp3_path}")
            return None

    def load_chords_from_hints(self) -> None:
        """Load chords from hints files if available."""
        hints_folder = os.path.join(self._songs_folder, "hints")
        chords_file = os.path.join(hints_folder, f"{self._song_name}.chords.json")

        if os.path.isfile(chords_file):
            with open(chords_file, "r") as f:
                self._chords = json.load(f)
            print(f" 📜 Chords loaded from {chords_file}")
        else:
            print(f"⚠️ Warning: Chords file not found for '{self._song_name}' at {chords_file}")

    def load_arrangement_from_hints(self) -> bool:
        """Load arrangement from hints files if available."""
        hints_folder = os.path.join(self._songs_folder, "hints")
        segments_file = os.path.join(hints_folder, f"{self._song_name}.segments.json")
        if not os.path.isfile(segments_file):
            return False
        with open(segments_file, "r") as f:
            segments_data = json.load(f)
        print(f" 📜 Segments loaded from {segments_file}")

        # convert segments to arrangement (list of Section)
        self.arrangement = [
            Section(
                name=segment.get("label") or segment.get("name", ""),
                start=segment["start"],
                end=segment["end"],
                prompt=segment.get("prompt", "")
            ) for segment in segments_data
        ]
        print(f"    .. {len(self._arrangement)} sections created")
        return True

    def load_key_moments_from_hints(self) -> bool:
        """Load key moments from hints files if available."""
        hints_folder = os.path.join(self._songs_folder, "hints")
        key_moments_file = os.path.join(hints_folder, f"{self._song_name}.key_moments.json")
        if not os.path.isfile(key_moments_file):
            print(f"⚠️ Warning: Key moments file not found for '{self._song_name}' at {key_moments_file}")
            return False
        with open(key_moments_file, "r") as f:
            key_moments_data = json.load(f)
        self.key_moments = key_moments_data
        print(f" 📜 Key moments loaded from {key_moments_file}")
        print(f"    .. {len(self.key_moments)} key moments loaded")
        return True

    def _load_hints_files(self) -> None:
        """Try to locate the hints files for this song."""
        hints_folder = os.path.join(self._songs_folder, "hints")
        if not os.path.isdir(hints_folder):
            print(f"⚠️ Warning: Hints folder not found for '{self._song_name}' at {hints_folder}")
            return

        # chords file
        self.load_chords_from_hints()

        # lyrics file
        lyrics_file = os.path.join(hints_folder, f"{self._song_name}.lyrics.json")
        if os.path.isfile(lyrics_file):
            with open(lyrics_file, "r") as f:
                lyrics_data = json.load(f)
            print(f" 📜 Lyrics loaded from {lyrics_file}")

        # segments file
        self.load_arrangement_from_hints()

        # key moments file
        self.load_key_moments_from_hints()

    def get_metadata_path(self) -> str:
        return os.path.join(self._songs_folder, f"{self._song_name}.meta.json")

    def exists(self) -> bool:
        return os.path.isfile(self.get_metadata_path())

    def load(self) -> None:
        with open(self.get_metadata_path(), "r") as f:
            data = json.load(f)

        self._title = data.get("title", self.title)
        self._genre = data.get("genre", self.genre)
        self._bpm = data.get("bpm", self.bpm)
        self._beats = data.get("beats", [])
        self._patterns = data.get("patterns", [])
        self._chords = data.get("chords", [])
        self._drums = data.get("drums", [])
        self._duration = data.get("duration", 0.0)
        self._arrangement = data.get("arrangement", [])
        self._key_moments = data.get("key_moments", [])

        # attempt to load hints files if not already done
        if len(self.beats) == 0:
            self.load_chords_from_hints()
        if len(self._arrangement) == 0:
            self.load_arrangement_from_hints()
        if len(self._key_moments) == 0:
            loaded = self.load_key_moments_from_hints()
            if not loaded:
                # fallback to default key moments if not loaded
                self.key_moments = [
                    {"time": 0.0, "name": "Song Start", "description": "Beginning of the song", "duration": 0},
                    {"time": 1.0, "name": "Drop", "description": "Main drop or beat drop", "duration": 0},
                    {"time": 2.0, "name": "Break", "description": "Breakdown or break section", "duration": 0},
                    {"time": 2.5, "name": "Build", "description": "Build-up section", "duration": 0},
                ]

    def initialize_song_metadata(self) -> None:
        """Initialize song metadata with default values."""
        # look for hints files
        self._load_hints_files()
        
        self.beats = [
            {"time": 0.5, "volume": 0.2, "energy": 0.3},
            {"time": 1.0, "volume": 0.4, "energy": 0.5},
            {"time": 1.5, "volume": 0.6, "energy": 0.7},
            {"time": 2.0, "volume": 0.5, "energy": 0.6},
            {"time": 2.5, "volume": 0.3, "energy": 0.4},
        ]

        if len(self._arrangement) == 0:
            self.arrangement = [
                Section("intro", 0.0, 0.5, "Intro section with ambient sounds. (placeholder)"),
                Section("verse", 0.5, 1.5, "Verse with minimal instrumentation and vocals."),
                Section("chorus", 1.5, 2.0, "Chorus with full energy and instrumentation."),
                Section("bridge", 2.0, 2.5, "Bridge section with rhythmic variation."),
                Section("outro", 2.5, 3.0, "Outro with fade-out or reduced energy.")
            ]

        if len(self._key_moments) == 0:
            self.key_moments = [
                {"time": 0.0, "name": "Song Start", "description": "Beginning of the song", "duration": 0},
                {"time": 1.0, "name": "Drop", "description": "Main drop or beat drop", "duration": 0},
                {"time": 2.0, "name": "Break", "description": "Breakdown or break section", "duration": 0},
                {"time": 2.5, "name": "Build", "description": "Build-up section", "duration": 0},
            ]

    def add_beat(self, time: float, volume: float = 0.0, energy: float = 1.0) -> None:
        self.beats.append({"time": time, "volume": volume, "energy": energy})

    def clear_beats(self) -> None:
        self.beats = []

    def get_beats_array(self) -> List[float]:
        return [beat["time"] for beat in self.beats]

    def set_beats_volume(self, beat_volume: List[Tuple[float, float]]) -> None:
        if len(beat_volume) != len(self.beats):
            print(f"⚠️ Warning: Volume list length {len(beat_volume)} does not match number of beats {len(self.beats)}.")
            return
        for i, (time, volume) in enumerate(beat_volume):
            if abs(self.beats[i]["time"] - time) > 1e-6:
                print(f"⚠️ Warning: Beat time mismatch at index {i}: expected {self.beats[i]['time']}, got {time}")
            self.beats[i]["volume"] = float(volume)

    def set_beats_energy(self, beat_energy: List[Tuple[float, float]]) -> None:
        if len(beat_energy) != len(self.beats):
            print(f"⚠️ Warning: Energy list length {len(beat_energy)} does not match number of beats {len(self.beats)}.")
            return
        for i, (time, energy) in enumerate(beat_energy):
            if abs(self.beats[i]["time"] - time) > 1e-6:
                print(f"⚠️ Warning: Beat time mismatch at index {i}: expected {self.beats[i]['time']}, got {time}")
            self.beats[i]["energy"] = float(energy)

    def update_beat(self, time: float, volume: Optional[float] = None, energy: Optional[float] = None) -> None:
        for beat in self.beats:
            if beat["time"] == time:
                if volume is not None:
                    beat["volume"] = volume
                if energy is not None:
                    beat["energy"] = energy
                return
        print(f"⚠️ Beat at time {time} not found.")

    def clear_patterns(self) -> None:
        """Clears all patterns from the song metadata."""
        self._patterns = []

    def add_patterns(self, stem_name: str, patterns: List[Dict[str, Any]]) -> None:
        """Adds patterns for a given stem to the song metadata."""
        if not hasattr(self, "_patterns"):
            self._patterns = []
        self._patterns.append({"stem": stem_name, "clusters": patterns})

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "title": self.title,
            "genre": self.genre,
            "duration": self.duration,
            "bpm": self.bpm,
            "chords": self.chords,
            "beats": self.beats,
            "drums": self.drums,
            "patterns": self._patterns,
            # Serialize arrangement as list of dicts
            "arrangement": [s.to_dict() if isinstance(s, Section) else s for s in self.arrangement],
            "key_moments": self.key_moments,
        }
        # Ensure all data is JSON serializable
        return ensure_json_serializable(data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def save(self) -> None:
        os.makedirs(self._songs_folder, exist_ok=True)
        with open(self.get_metadata_path(), "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"ℹ️ Metadata saved for '{self._song_name}' at {self.get_metadata_path()}")

    def __str__(self) -> str:
        return f"SongMetadata(song_name={self._song_name}, title={self.title}, genre={self.genre}, bpm={self.bpm}, duration={self.duration}, beats={len(self.beats)}, arrangement={len(self.arrangement)})"
