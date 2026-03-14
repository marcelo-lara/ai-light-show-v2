from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CueEntry(BaseModel):
    time: float
    fixture_id: str
    effect: str
    duration: float = 0.0
    data: Dict[str, Any] = Field(default_factory=dict)
    name: Optional[str] = None
    created_by: str = "user"


class CueSheet(BaseModel):
    song_filename: str
    entries: List[CueEntry] = Field(default_factory=list)
