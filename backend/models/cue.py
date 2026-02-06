from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class CueEntry(BaseModel):
    """A single high-level cue instruction.

    Cue sheets are effect-based: each entry names a fixture `effect` plus
    parameters that the fixture type interprets while rendering the DMX canvas.

    See docs/architecture.md.
    """

    time: float  # seconds
    fixture_id: str
    effect: str
    duration: float = 0.0  # seconds
    data: Dict[str, Any] = {}
    name: Optional[str] = None


class CueSheet(BaseModel):
    song_filename: str
    entries: List[CueEntry]