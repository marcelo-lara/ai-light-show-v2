from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class Fixture(BaseModel):
    id: str
    name: str
    type: str
    channels: Dict[str, int]
    current_values: Dict[str, Any]
    presets: List[Dict[str, Any]]
    actions: List[str]
    arm: Dict[str, int]
    meta: Dict[str, Any]