from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class SongMetadata(BaseModel):
    filename: str
    length: Optional[float] = None  # seconds
    bpm: Optional[float] = None
    key: Optional[str] = None
    parts: Dict[str, List[float]] = Field(default_factory=dict)
    hints: Dict[str, List[float]] = Field(default_factory=dict)
    drums: Dict[str, List[float]] = Field(default_factory=dict)

class Song(BaseModel):
    filename: str
    metadata: SongMetadata
    audioUrl: Optional[str] = None
