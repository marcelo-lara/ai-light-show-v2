import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .meta import Meta
from .beats import Beats
from .sections import Sections
from .io import load_meta_data, load_beats_data, load_sections_data, save_sections_data

class Song:
    """
    Manages song metadata, beats, and sections.
    Uses lazy loading to avoid parsing files before they are requested.
    """
    def __init__(self, song_id: str, base_dir: str = "/app/meta", audio_url: Optional[str] = None):
        self.song_id = song_id
        if not self.song_id:
            raise ValueError("song_id must be provided")

        self.base_dir = Path(base_dir)
        self.song_dir = self.base_dir / self.song_id
        self.audio_url = audio_url
        
        self._meta: Optional[Meta] = None
        self._beats: Optional[Beats] = None
        self._sections: Optional[Sections] = None

    def _load_meta(self):
        if self._meta is None:
            self._meta = load_meta_data(self.song_dir, self.song_id)

    def _load_beats(self):
        if self._beats is None:
            self._load_meta()
            self._beats = load_beats_data(self._meta.beats_file)

    def _load_sections(self):
        if self._sections is None:
            self._sections = load_sections_data(self.song_dir)

    @property
    def meta(self) -> Meta:
        self._load_meta()
        return self._meta

    @property
    def beats(self) -> Beats:
        self._load_beats()
        return self._beats

    @property
    def bpm(self) -> int:
        self._load_meta()
        return self._meta.bpm if self._meta.bpm is not None else 120    
    
    @property
    def sections(self) -> Sections:
        self._load_sections()
        return self._sections

    def update_sections(self, new_sections: List[Dict[str, Any]]):
        save_sections_data(self.song_dir, new_sections)
        if self._sections is None:
            self._sections = Sections(sections=new_sections)
        else:
            self._sections.sections = new_sections
