from typing import List, Optional, Literal

from pydantic import BaseModel, model_validator

class Beat(BaseModel):
    time: float
    beat: int
    bar: int
    bass: Optional[str] = None
    chord: Optional[str] = None
    type: Literal["beat", "downbeat"]

    @model_validator(mode="before")
    @classmethod
    def _normalize_type(cls, value):
        if not isinstance(value, dict):
            return value
        beat_number = int(value.get("beat", 0) or 0)
        beat_type = value.get("type")
        if beat_type not in {"beat", "downbeat"}:
            value = dict(value)
            value["type"] = "downbeat" if beat_number == 1 else "beat"
        return value

class Beats(BaseModel):
    beats: List[Beat]
