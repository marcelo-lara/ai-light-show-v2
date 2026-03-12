from pydantic import BaseModel
from typing import Dict, Any

class Meta(BaseModel):
    song_name: str
    bpm: float
    duration: float
    beats_file: str
    song_key: str
    artifacts: Dict[str, Any]
