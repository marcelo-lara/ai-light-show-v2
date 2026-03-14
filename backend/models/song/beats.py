from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Beat(BaseModel):
    time: float
    beat: int
    bar: int
    bass: Optional[str] = None
    chord: Optional[str] = None

class Beats(BaseModel):
    beats: List[Beat]
