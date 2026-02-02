from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class CueEntry(BaseModel):
    timecode: float  # in seconds
    name: Optional[str] = None
    values: Dict[str, Dict[str, Any]]  # fixture_id -> {channel: value}

class CueSheet(BaseModel):
    song_filename: str
    entries: List["CueEntry"]