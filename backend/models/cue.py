from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class CueEntry(BaseModel):
    """A single high-level cue instruction.

    This matches docs/dmx_dispatcher.md: the cue sheet is a list of actions that
    fixtures interpret to render intermediate DMX frames.
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