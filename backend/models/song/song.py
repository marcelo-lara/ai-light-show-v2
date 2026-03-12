import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Meta:
    song_name: str
    bpm: float
    duration: float
    beats_file: str
    song_key: str
    artifacts: Dict[str, Any]

@dataclass
class Beats:
    beats: List[float]
    downbeats: List[float]
    beats_array: List[Dict[str, Any]]

@dataclass
class Sections:
    sections: List[Dict[str, Any]]

class Song:
    """
    Manages song metadata, beats, and sections.
    Uses lazy loading to avoid parsing files before they are requested.
    """
    def __init__(self, song_id: str, base_dir: str = "/app/meta"):
        self.song_id = song_id
        self.base_dir = Path(base_dir)
        self.song_dir = self.base_dir / song_id
        
        # Internal state for lazy loading
        self._meta: Optional[Meta] = None
        self._beats: Optional[Beats] = None
        self._sections: Optional[Sections] = None

    def _load_meta(self):
        if self._meta is not None:
            return

        info_path = self.song_dir / "info.json"
        
        if not info_path.exists():
            raise FileNotFoundError(f"Missing info.json at {info_path}")
            
        with open(info_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Optional fallback for beats_file if it's not strictly defined in info.json
        # Usually it's in the song_dir as beats.json
        beats_file = data.get("beats_file", str(self.song_dir / "beats.json"))
            
        self._meta = Meta(
            song_name=data.get("song_name", self.song_id),
            bpm=data.get("bpm", 0.0),
            duration=data.get("duration", 0.0),
            beats_file=beats_file,
            song_key=data.get("song_key", ""),
            artifacts=data.get("artifacts", {})
        )

    def _load_beats(self):
        if self._beats is not None:
            return
            
        self._load_meta()
        beats_path = Path(self._meta.beats_file)
        
        beats = []
        downbeats = []
        
        if beats_path.exists():
            with open(beats_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                beats = data.get("beats", [])
                downbeats = data.get("downbeats", [])
                
        # Consolidate and sort by time
        beats_array = []
        for b in beats:
            beats_array.append({"time": b, "type": "beat"})
        for d in downbeats:
            # We add downbeats. If a downbeat has exactly the same time as a beat, it's fine 
            # or could be filtered to replace the beat if that's the domain logic, 
            # but usually they are distinct arrays, and appending both gets you a full timeline.
            beats_array.append({"time": d, "type": "downbeat"})
            
        beats_array.sort(key=lambda x: x["time"])
        
        self._beats = Beats(
            beats=beats,
            downbeats=downbeats,
            beats_array=beats_array
        )

    def _load_sections(self):
        if self._sections is not None:
            return
            
        sections_path = self.song_dir / "sections.json"
        sections_data = []
        
        if sections_path.exists():
            with open(sections_path, 'r', encoding='utf-8') as f:
                sections_data = json.load(f)
                if isinstance(sections_data, dict) and "sections" in sections_data:
                    sections_data = sections_data["sections"]
        else:
            # Create if it doesn't exist
            self._save_sections([])
            
        self._sections = Sections(sections=sections_data)

    def _save_sections(self, sections: List[Dict[str, Any]]):
        sections_path = self.song_dir / "sections.json"
        
        # Ensure parent directory exists
        sections_path.parent.mkdir(parents=True, exist_ok=True)
            
        with open(sections_path, 'w', encoding='utf-8') as f:
            json.dump(sections, f, indent=4)

    # --- Public API (Properties) ---

    @property
    def meta(self) -> Meta:
        self._load_meta()
        return self._meta

    @property
    def beats(self) -> Beats:
        self._load_beats()
        return self._beats

    @property
    def sections(self) -> Sections:
        self._load_sections()
        return self._sections

    # --- Public API (Methods) ---

    def update_sections(self, new_sections: List[Dict[str, Any]]):
        """
        Updates the sections and writes them back to sections.json.
        """
        # Save to disk
        self._save_sections(new_sections)
        # Update in memory
        if self._sections is None:
            self._sections = Sections(sections=new_sections)
        else:
            self._sections.sections = new_sections
