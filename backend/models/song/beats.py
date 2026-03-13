from pydantic import BaseModel
from typing import List, Dict, Any

class Beat(BaseModel):
    time: float
    beat: int
    bar: int
    bass: str
    chord: str

class Beats(BaseModel):
    beats: List[Beat]
