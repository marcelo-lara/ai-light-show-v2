from pydantic import BaseModel
from typing import List, Dict, Any

class Beats(BaseModel):
    beats: List[float]
    downbeats: List[float]
    beats_array: List[Dict[str, Any]]
