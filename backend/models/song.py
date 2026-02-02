from pydantic import BaseModel
from typing import Dict, List, Optional

class SongMetadata(BaseModel):
    filename: str
    length: float  # seconds
    bpm: Optional[float] = None
    key: Optional[str] = None
    parts: Dict[str, List[float]]  # e.g., {"intro": [0.0, 30.0], "verse": [30.0, 60.0], ...}
    hints: Dict[str, List[float]]  # e.g., {"drops": [15.0, 45.0], ...}
    drums: Dict[str, List[float]]  # e.g., {"kicks": [...], "snares": [...], "hihats": [...]}

class Song(BaseModel):
    filename: str
    metadata: SongMetadata
    audioUrl: Optional[str] = None