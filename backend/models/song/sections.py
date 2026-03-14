from pydantic import BaseModel
from typing import List, Dict, Any

class Sections(BaseModel):
    sections: List[Dict[str, Any]]
