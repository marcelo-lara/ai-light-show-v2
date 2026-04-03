import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .meta import Meta
from .beats import Beats, Beat
from .sections import Sections


def _is_supported_beats_path(path: Path) -> bool:
    return path.parent.name in {"reference", "inferred"}


def _resolve_meta_path(path: Path, song_dir: Path) -> Path:
    if path.exists() or not path.is_absolute():
        return path
    try:
        relative = path.relative_to("/app/meta")
    except ValueError:
        return path
    return song_dir.parent / relative


def resolve_beats_file(song_dir: Path, info_data: Dict[str, Any] | None = None) -> str:
    default_path = str(song_dir / "reference" / "beats.json")
    if not isinstance(info_data, dict):
        return default_path
    beats_file = info_data.get("beats_file")
    if isinstance(beats_file, str) and beats_file:
        beats_path = _resolve_meta_path(Path(beats_file), song_dir)
        if _is_supported_beats_path(beats_path):
            return str(beats_path)
    artifacts = info_data.get("artifacts")
    if isinstance(artifacts, dict):
        artifact_beats_file = artifacts.get("beats_file")
        if isinstance(artifact_beats_file, str) and artifact_beats_file:
            beats_path = _resolve_meta_path(Path(artifact_beats_file), song_dir)
            if _is_supported_beats_path(beats_path):
                return str(beats_path)
    return default_path

def load_meta_data(song_dir: Path, song_id: str) -> Meta:
    info_path = song_dir / "info.json"
    beats_file = resolve_beats_file(song_dir)
    if not info_path.exists():
        return Meta(
            song_name=song_id,
            bpm=0.0,
            duration=0.0,
            beats_file=beats_file,
            song_key="",
            artifacts={},
        )
        
    with open(info_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    beats_file = resolve_beats_file(song_dir, data)
        
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
                raise ValueError(f"Invalid beats format at {beats_path}: expected list of beat objects")
    
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
