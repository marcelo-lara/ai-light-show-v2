import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .meta import Meta
from .beats import Beats, Beat
from .sections import Sections

def load_meta_data(song_dir: Path, song_id: str) -> Meta:
    info_path = song_dir / "info.json"
    if not info_path.exists():
        raise FileNotFoundError(f"Missing info.json at {info_path}")
        
    with open(info_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    beats_file = data.get("beats_file", str(song_dir / "beats.json"))
        
    return Meta(
        song_name=data.get("song_name", song_id),
        bpm=data.get("bpm", 0.0),
        duration=data.get("duration", 0.0),
        beats_file=beats_file,
        song_key=data.get("song_key", ""),
        artifacts=data.get("artifacts", {})
    )

def load_beats_data(beats_file: str) -> Beats:
    beats_path = Path(beats_file)
    beat_list = []
    
    if beats_path.exists():
        with open(beats_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    beat_list.append(Beat(**item))
            else:
                # Fallback for old schema, but we are hard-breaking
                raise ValueError(f"Invalid beats.json format at {beats_path}: expected list of beat objects")
    
    return Beats(beats=beat_list)

def load_sections_data(song_dir: Path) -> Sections:
    sections_path = song_dir / "sections.json"
    sections_data = []
    
    if sections_path.exists():
        with open(sections_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and "sections" in data:
                sections_data = data["sections"]
            elif isinstance(data, list):
                sections_data = data
                
    return Sections(sections=sections_data)

def save_sections_data(song_dir: Path, sections: List[Dict[str, Any]]):
    sections_path = song_dir / "sections.json"
    sections_path.parent.mkdir(parents=True, exist_ok=True)
        
    with open(sections_path, 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=4)
